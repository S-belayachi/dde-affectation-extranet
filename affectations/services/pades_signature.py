import hashlib
import logging
from dataclasses import dataclass
from datetime import timedelta, timezone as datetime_timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from pyhanko.pdf_utils import layout
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign import signers
from pyhanko.sign.diff_analysis import ModificationLevel
from pyhanko.sign.fields import SigFieldSpec, SigSeedSubFilter
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko.sign.validation.pdf_embedded import SignatureCoverageLevel
from pyhanko.stamp import StaticStampStyle
from pyhanko_certvalidator import ValidationContext


logger = logging.getLogger(__name__)

PADES_PROFILE = "PAdES-B-B"


class PadesSignatureError(Exception):
    """Raised when the development PAdES signature cannot be created."""


@dataclass(frozen=True)
class PadesSignatureDetails:
    profile: str
    field_name: str
    certificate_subject: str
    certificate_serial_number: str
    certificate_fingerprint_sha256: str


@dataclass(frozen=True)
class PadesValidationResult:
    is_valid: bool
    signature_present: bool = False
    field_name: str = ""
    certificate_subject: str = ""
    certificate_fingerprint_sha256: str = ""
    error: str = ""


def signer_full_name(signer):
    first_name = " ".join((signer.first_name or "").split())
    last_name = " ".join((signer.last_name or "").split())
    if not first_name or not last_name:
        raise PadesSignatureError(
            "Le prenom et le nom reels du signataire doivent etre renseignes."
        )
    return f"{first_name} {last_name}"


def build_ephemeral_signer(signer, administration, signed_at):
    full_name = signer_full_name(signer)
    administration_name = " ".join((administration.nom or "").split())
    if not administration_name:
        raise PadesSignatureError(
            "Le nom de l'administration beneficiaire doit etre renseigne."
        )

    certificate_time = signed_at.astimezone(datetime_timezone.utc)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name(
        [
            x509.NameAttribute(NameOID.COMMON_NAME, full_name),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, administration_name),
        ]
    )
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(certificate_time - timedelta(minutes=5))
        .not_valid_after(certificate_time + timedelta(days=365))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )
    pkcs12_data = pkcs12.serialize_key_and_certificates(
        name=b"pv-beneficiary-signature",
        key=private_key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pades_signer = signers.SimpleSigner.load_pkcs12_data(
        pkcs12_data,
        other_certs=[],
    )
    if pades_signer is None:
        raise PadesSignatureError(
            "Le certificat PAdES temporaire n'a pas pu etre charge."
        )

    details = PadesSignatureDetails(
        profile=PADES_PROFILE,
        field_name="",
        certificate_subject=certificate.subject.rfc4514_string(),
        certificate_serial_number=format(certificate.serial_number, "x"),
        certificate_fingerprint_sha256=certificate.fingerprint(
            hashes.SHA256()
        ).hex(),
    )
    return pades_signer, details, full_name


def sign_pdf_with_pades(
    input_path,
    output_path,
    signer,
    administration,
    signed_at,
    field_name,
    *,
    field_box=None,
    field_page=0,
    appearance_pdf_path=None,
):
    input_path = Path(input_path)
    output_path = Path(output_path)
    pades_signer, certificate_details, full_name = build_ephemeral_signer(
        signer,
        administration,
        signed_at,
    )
    metadata = signers.PdfSignatureMetadata(
        field_name=field_name,
        md_algorithm="sha256",
        subfilter=SigSeedSubFilter.PADES,
        name=full_name,
        reason="Signature electronique du PV d'affectation",
    )

    try:
        with open(input_path, "rb") as source, open(output_path, "wb") as output:
            writer = IncrementalPdfFileWriter(source)
            field_spec = SigFieldSpec(
                field_name,
                on_page=field_page,
                box=field_box,
            )
            stamp_style = (
                StaticStampStyle.from_pdf_file(
                    appearance_pdf_path,
                    border_width=0,
                    background_opacity=1,
                    background_layout=layout.SimpleBoxLayoutRule(
                        x_align=layout.AxisAlignment.ALIGN_MID,
                        y_align=layout.AxisAlignment.ALIGN_MID,
                        margins=layout.Margins.uniform(0),
                    ),
                )
                if appearance_pdf_path
                else None
            )
            pdf_signer = signers.PdfSigner(
                signature_meta=metadata,
                signer=pades_signer,
                stamp_style=stamp_style,
                new_field_spec=field_spec,
            )
            pdf_signer.sign_pdf(
                writer,
                output=output,
            )
    except Exception as error:
        raise PadesSignatureError(
            "La signature cryptographique PAdES du PDF a echoue."
        ) from error

    return PadesSignatureDetails(
        profile=certificate_details.profile,
        field_name=field_name,
        certificate_subject=certificate_details.certificate_subject,
        certificate_serial_number=certificate_details.certificate_serial_number,
        certificate_fingerprint_sha256=(
            certificate_details.certificate_fingerprint_sha256
        ),
    )


def validate_pades_signature(
    path,
    expected_field_name="",
    expected_fingerprint_sha256="",
    allow_later_signatures=False,
):
    try:
        with open(path, "rb") as signed_file:
            reader = PdfFileReader(signed_file)
            signatures = reader.embedded_signatures
            if expected_field_name:
                embedded_signature = next(
                    (
                        signature
                        for signature in signatures
                        if signature.field_name == expected_field_name
                    ),
                    None,
                )
            else:
                embedded_signature = signatures[-1] if signatures else None

            if embedded_signature is None:
                return PadesValidationResult(
                    is_valid=False,
                    error="Signature PAdES absente.",
                )

            signer_certificate = embedded_signature.signer_cert
            fingerprint = hashlib.sha256(signer_certificate.dump()).hexdigest()
            validation_context = ValidationContext(
                trust_roots=[signer_certificate],
                allow_fetching=False,
            )
            status = validate_pdf_signature(
                embedded_signature,
                signer_validation_context=validation_context,
            )
            fingerprint_matches = (
                not expected_fingerprint_sha256
                or fingerprint.lower() == expected_fingerprint_sha256.lower()
            )
            if allow_later_signatures:
                revision_is_acceptable = bool(
                    status.coverage
                    in {
                        SignatureCoverageLevel.ENTIRE_REVISION,
                        SignatureCoverageLevel.ENTIRE_FILE,
                    }
                    and status.modification_level
                    in {
                        ModificationLevel.NONE,
                        ModificationLevel.FORM_FILLING,
                    }
                )
            else:
                revision_is_acceptable = bool(
                    status.coverage == SignatureCoverageLevel.ENTIRE_FILE
                    and status.modification_level == ModificationLevel.NONE
                )

            is_valid = bool(
                fingerprint_matches
                and status.valid
                and status.intact
                and status.bottom_line
                and status.docmdp_ok
                and revision_is_acceptable
            )
            return PadesValidationResult(
                is_valid=is_valid,
                signature_present=True,
                field_name=embedded_signature.field_name,
                certificate_subject=signer_certificate.subject.human_friendly,
                certificate_fingerprint_sha256=fingerprint,
                error="" if is_valid else "Signature PAdES invalide ou PDF modifie.",
            )
    except Exception:
        logger.exception("PAdES validation failed for %s", path)
        return PadesValidationResult(
            is_valid=False,
            error="Le PDF ou sa signature PAdES ne peut pas etre valide.",
        )
