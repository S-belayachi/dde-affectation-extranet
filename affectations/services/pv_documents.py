import hashlib
import re
import tempfile
from dataclasses import dataclass
from html import escape
from pathlib import Path

import fitz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from affectations.models import PvAffectation
from affectations.services.pades_signature import (
    PadesSignatureDetails,
    PadesSignatureError,
    sign_pdf_with_pades,
    validate_pades_signature,
)
from affectations.services.pv_rules import build_pv_key


ELECTRONIC_SIGNATURE_FOOTER_HEIGHT = 84
INTEGRITY_VALID = "valid"
INTEGRITY_TAMPERED = "tampered"
INTEGRITY_MISSING = "missing"
INTEGRITY_UNVERIFIABLE = "unverifiable"
INTEGRITY_NOT_SIGNED = "not_signed"


@dataclass(frozen=True)
class SignedPvIntegrityResult:
    status: str
    current_hash: str = ""
    pv_hash: str = ""
    proof_hash: str = ""
    path: Path | None = None
    pades_valid: bool = False
    pades_subject: str = ""
    pades_error: str = ""

    @property
    def is_valid(self):
        return self.status == INTEGRITY_VALID


class OfficialPvError(Exception):
    """Base error for official AMLACS PV retrieval and signing."""


class OfficialPvNotFoundError(OfficialPvError):
    pass


class OfficialPvAmbiguousError(OfficialPvError):
    pass


class OfficialPvChangedError(OfficialPvError):
    pass


@dataclass(frozen=True)
class SignedPdfResult:
    sha256: str
    pades: PadesSignatureDetails


def calculate_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_filename_part(value):
    value = "" if value is None else str(value).strip()
    return re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")


def get_or_create_pv(dossier, administration):
    pv_key = build_pv_key(dossier)
    pv, _created = PvAffectation.objects.get_or_create(
        pv_key=pv_key,
        defaults={
            "source_import_id": dossier.import_id,
            "num_dossier": dossier.num_dossier,
            "numero_pv": dossier.numero_pv,
            "administration_source_nom": dossier.administration_beneficiaire or "",
            "administration": administration,
        },
    )
    return pv


def source_filename_candidates(dossier, pv):
    dossier_part = safe_filename_part(dossier.num_dossier)
    pv_part = safe_filename_part(dossier.numero_pv)
    candidates = [f"{dossier.import_id}.pdf", f"{pv.pv_key}.pdf"]

    if dossier_part:
        candidates.append(f"{dossier_part}.pdf")
    if dossier_part and pv_part:
        candidates.append(f"{dossier_part}__{pv_part}.pdf")
    if pv_part:
        candidates.append(f"{pv_part}.pdf")

    return candidates


def safe_path(root, relative_name):
    root = Path(root).resolve()
    candidate = (root / relative_name).resolve()
    if candidate != root and root not in candidate.parents:
        raise OfficialPvError("Chemin de PV invalide.")
    return candidate


def resolve_official_pdf(dossier, pv):
    official_root = Path(settings.AMLACS_PV_OFFICIAL_ROOT)
    if not official_root.is_dir():
        raise OfficialPvNotFoundError("Le repertoire des PV AMLACS est introuvable.")

    if pv.source_filename:
        known_path = safe_path(official_root, pv.source_filename)
        if known_path.is_file() and known_path.suffix.lower() == ".pdf":
            return known_path

    matches = [
        official_root / name
        for name in source_filename_candidates(dossier, pv)
        if (official_root / name).is_file()
    ]
    matches = list(dict.fromkeys(matches))

    if not matches:
        raise OfficialPvNotFoundError(
            "Le PV officiel AMLACS est absent du repertoire prive."
        )
    if len(matches) > 1:
        raise OfficialPvAmbiguousError(
            "Plusieurs PDF AMLACS correspondent a ce PV."
        )
    return matches[0]


def retrieve_official_pv(dossier, administration):
    pv = get_or_create_pv(dossier, administration)
    source_path = resolve_official_pdf(dossier, pv)
    source_hash = calculate_sha256(source_path)

    pv.source_filename = source_path.name
    pv.source_pdf_hash_sha256 = source_hash
    pv.source_retrieved_at = timezone.now()
    pv.save(
        update_fields=[
            "source_filename",
            "source_pdf_hash_sha256",
            "source_retrieved_at",
        ]
    )
    return pv, source_path


def single_line_text(value):
    return " ".join(str(value or "").split())


def electronic_signature_statement(administration, signer, signed_at):
    signer_name_ar = " ".join(
        part
        for part in (
            single_line_text(getattr(signer, "prenom_ar", "")),
            single_line_text(getattr(signer, "nom_ar", "")),
        )
        if part
    )
    signer_name = signer_name_ar or single_line_text(signer.get_full_name())
    if not signer_name:
        raise OfficialPvError(
            "Le nom et le prenom du signataire doivent etre renseignes."
        )

    administration_name = (
        single_line_text(administration.nom_ar)
        or single_line_text(administration.nom)
    )
    local_signed_at = timezone.localtime(signed_at)

    return (
        f"تم توقيع هذا المحضر إلكترونياً من طرف {signer_name}، "
        f"نيابةً عن الإدارة المستفيدة {administration_name}، "
        f"بتاريخ {local_signed_at:%d/%m/%Y} "
        f"على الساعة {local_signed_at:%H:%M:%S}"
    )


def dr_electronic_signature_statement(delegation, signer, signed_at):
    signer_name_ar = " ".join(
        part
        for part in (
            single_line_text(getattr(signer, "prenom_ar", "")),
            single_line_text(getattr(signer, "nom_ar", "")),
        )
        if part
    )
    signer_name = signer_name_ar or single_line_text(signer.get_full_name())
    if not signer_name:
        raise OfficialPvError(
            "Le nom et le prenom du signataire DR doivent etre renseignes."
        )

    local_signed_at = timezone.localtime(signed_at)
    return (
        f"تم توقيع هذا المحضر إلكترونياً من طرف {signer_name}، "
        f"نيابةً عن مندوبية أملاك الدولة {single_line_text(delegation.nom)}، "
        f"بتاريخ {local_signed_at:%d/%m/%Y} "
        f"على الساعة {local_signed_at:%H:%M:%S}"
    )


def absolute_signed_path(relative_path):
    return safe_path(settings.PV_DOCUMENT_ROOT, relative_path)


def signed_relative_path(pv):
    document_root = Path(settings.PV_DOCUMENT_ROOT).resolve()
    signed_root = Path(settings.SIGNED_PV_ROOT).resolve()
    try:
        relative_directory = signed_root.relative_to(document_root)
    except ValueError as error:
        raise OfficialPvError(
            "Le repertoire des PV signes doit rester sous PV_DOCUMENT_ROOT."
        ) from error
    return str(relative_directory / f"{pv.pv_key}.pdf")


def dr_signed_relative_path(pv):
    document_root = Path(settings.PV_DOCUMENT_ROOT).resolve()
    signed_root = Path(settings.DR_SIGNED_PV_ROOT).resolve()
    try:
        relative_directory = signed_root.relative_to(document_root)
    except ValueError as error:
        raise OfficialPvError(
            "Le repertoire des PV DR doit rester sous PV_DOCUMENT_ROOT."
        ) from error
    return str(relative_directory / f"{pv.pv_key}.pdf")


def _create_pades_signed_copy(
    source_path,
    output_path,
    signature_statement,
    signer,
    organization,
    signed_at,
    field_name,
    reserved_footer_slots=1,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stamped_temporary_path = None
    signed_temporary_path = None
    document = None
    pades_details = None

    try:
        document = fitz.open(source_path)
        if document.page_count == 0:
            raise OfficialPvError("Le PDF officiel est vide.")

        page = document[document.page_count - 1]
        original_page_height = page.rect.height
        reserved_footer_height = (
            ELECTRONIC_SIGNATURE_FOOTER_HEIGHT * reserved_footer_slots
        )
        media_box = page.mediabox
        page.set_mediabox(
            fitz.Rect(
                media_box.x0,
                media_box.y0 - reserved_footer_height,
                media_box.x1,
                media_box.y1,
            )
        )
        page_rect = page.rect
        separator_y = original_page_height + 8
        page.draw_line(
            fitz.Point(page_rect.x0 + 36, separator_y),
            fitz.Point(page_rect.x1 - 36, separator_y),
            color=(0.65, 0.7, 0.74),
            width=0.6,
            overlay=True,
        )
        footer = fitz.Rect(
            page_rect.x0 + 36,
            separator_y + 8,
            page_rect.x1 - 36,
            original_page_height + ELECTRONIC_SIGNATURE_FOOTER_HEIGHT - 8,
        )
        arabic_font_path = Path(settings.PV_ARABIC_FONT_PATH).resolve()
        if not arabic_font_path.is_file():
            raise OfficialPvError(
                "La police arabe du pied de page est introuvable."
            )
        font_archive = fitz.Archive(arabic_font_path.parent)
        local_signed_at = timezone.localtime(signed_at)
        signature_date = local_signed_at.strftime("%d/%m/%Y")
        signature_time = local_signed_at.strftime("%H:%M:%S")
        signature_moment = (
            f"بتاريخ {signature_date} على الساعة {signature_time}"
        )
        signature_moment_html = (
            '<span class="signature-moment" dir="rtl">'
            'بتاريخ '
            f'<span class="signature-value" dir="ltr">{signature_date}</span> '
            'على الساعة '
            f'<span class="signature-value" dir="ltr">{signature_time}</span>'
            '</span>'
        )
        signature_statement_html = escape(signature_statement).replace(
            escape(signature_moment),
            signature_moment_html,
            1,
        )
        html = (
            '<div class="signature" dir="rtl" lang="ar">'
            f"{signature_statement_html}</div>"
        )
        css = f"""
            @font-face {{
                font-family: PvArabic;
                src: url({arabic_font_path.name});
            }}
            .signature {{
                font-family: PvArabic;
                font-size: 10pt;
                line-height: 1.5;
                text-align: center;
                color: #1f2933;
            }}
            .signature-value {{
                direction: ltr;
            }}
            .signature-moment {{
                white-space: nowrap;
            }}
        """
        remaining_height, _scale = page.insert_htmlbox(
            footer,
            html,
            css=css,
            archive=font_archive,
            scale_low=1,
            overlay=True,
        )
        if remaining_height < 0:
            raise OfficialPvError("La mention de signature ne tient pas dans le PDF.")

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=output_path.parent,
            delete=False,
        ) as temporary_file:
            stamped_temporary_path = Path(temporary_file.name)
        document.save(stamped_temporary_path, garbage=4, deflate=True)
        document.close()
        document = None

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=output_path.parent,
            delete=False,
        ) as temporary_file:
            signed_temporary_path = Path(temporary_file.name)
        pades_details = sign_pdf_with_pades(
            stamped_temporary_path,
            signed_temporary_path,
            signer,
            organization,
            signed_at,
            field_name=field_name,
        )
        signed_temporary_path.replace(output_path)
    except fitz.FileDataError as error:
        raise OfficialPvError("Le PDF officiel AMLACS est invalide.") from error
    except PadesSignatureError as error:
        raise OfficialPvError(str(error)) from error
    finally:
        if document is not None:
            document.close()
        for temporary_path in (stamped_temporary_path, signed_temporary_path):
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    return SignedPdfResult(
        sha256=calculate_sha256(output_path),
        pades=pades_details,
    )


def _create_incremental_beneficiary_signature(
    source_path,
    output_path,
    signature_statement,
    signer,
    administration,
    signed_at,
    field_name,
):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    appearance_path = None
    signed_temporary_path = None
    document = None
    appearance_document = None

    try:
        document = fitz.open(source_path)
        if document.page_count == 0:
            raise OfficialPvError("Le PDF signe par la DR est vide.")
        signed_page = document[-1]
        page_width = signed_page.rect.width
        media_box_bottom = signed_page.mediabox.y0
        document.close()
        document = None

        field_box = (
            36,
            int(media_box_bottom + 8),
            int(page_width - 36),
            int(
                media_box_bottom
                + ELECTRONIC_SIGNATURE_FOOTER_HEIGHT
                - 8
            ),
        )
        appearance_width = field_box[2] - field_box[0]
        appearance_height = field_box[3] - field_box[1]

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=output_path.parent,
            delete=False,
        ) as temporary_file:
            appearance_path = Path(temporary_file.name)

        appearance_document = fitz.open()
        appearance_page = appearance_document.new_page(
            width=appearance_width,
            height=appearance_height,
        )
        appearance_page.draw_line(
            fitz.Point(0, 1),
            fitz.Point(appearance_width, 1),
            color=(0.65, 0.7, 0.74),
            width=0.6,
        )
        arabic_font_path = Path(settings.PV_ARABIC_FONT_PATH).resolve()
        if not arabic_font_path.is_file():
            raise OfficialPvError(
                "La police arabe du pied de page est introuvable."
            )
        font_archive = fitz.Archive(arabic_font_path.parent)
        local_signed_at = timezone.localtime(signed_at)
        signature_date = local_signed_at.strftime("%d/%m/%Y")
        signature_time = local_signed_at.strftime("%H:%M:%S")
        signature_moment = (
            f"بتاريخ {signature_date} على الساعة {signature_time}"
        )
        signature_moment_html = (
            '<span class="signature-moment" dir="rtl">'
            'بتاريخ '
            f'<span class="signature-value" dir="ltr">{signature_date}</span> '
            'على الساعة '
            f'<span class="signature-value" dir="ltr">{signature_time}</span>'
            '</span>'
        )
        signature_statement_html = escape(signature_statement).replace(
            escape(signature_moment),
            signature_moment_html,
            1,
        )
        html = (
            '<div class="signature" dir="rtl" lang="ar">'
            f"{signature_statement_html}</div>"
        )
        css = f"""
            @font-face {{
                font-family: PvArabic;
                src: url({arabic_font_path.name});
            }}
            .signature {{
                font-family: PvArabic;
                font-size: 10pt;
                line-height: 1.5;
                text-align: center;
                color: #1f2933;
            }}
            .signature-value {{
                direction: ltr;
            }}
            .signature-moment {{
                white-space: nowrap;
            }}
        """
        remaining_height, _scale = appearance_page.insert_htmlbox(
            fitz.Rect(0, 8, appearance_width, appearance_height - 2),
            html,
            css=css,
            archive=font_archive,
            scale_low=1,
        )
        if remaining_height < 0:
            raise OfficialPvError(
                "La mention de signature beneficiaire ne tient pas dans le PDF."
            )
        appearance_document.save(
            appearance_path,
            garbage=4,
            deflate=True,
        )
        appearance_document.close()
        appearance_document = None

        with tempfile.NamedTemporaryFile(
            suffix=".pdf",
            dir=output_path.parent,
            delete=False,
        ) as temporary_file:
            signed_temporary_path = Path(temporary_file.name)
        pades_details = sign_pdf_with_pades(
            source_path,
            signed_temporary_path,
            signer,
            administration,
            signed_at,
            field_name=field_name,
            field_box=field_box,
            field_page=-1,
            appearance_pdf_path=appearance_path,
        )
        signed_temporary_path.replace(output_path)
    except fitz.FileDataError as error:
        raise OfficialPvError("Le PDF signe par la DR est invalide.") from error
    except PadesSignatureError as error:
        raise OfficialPvError(str(error)) from error
    finally:
        if document is not None:
            document.close()
        if appearance_document is not None:
            appearance_document.close()
        for temporary_path in (appearance_path, signed_temporary_path):
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()

    return SignedPdfResult(
        sha256=calculate_sha256(output_path),
        pades=pades_details,
    )


def _official_source_path_for_signing(pv):
    if not pv.source_filename or not pv.source_pdf_hash_sha256:
        raise OfficialPvError("Le PV officiel doit etre recupere avant signature.")

    source_path = safe_path(settings.AMLACS_PV_OFFICIAL_ROOT, pv.source_filename)
    if not source_path.is_file():
        raise OfficialPvNotFoundError("Le PV officiel AMLACS est introuvable.")
    if calculate_sha256(source_path) != pv.source_pdf_hash_sha256:
        raise OfficialPvChangedError(
            "Le PV officiel a change. Demandez un nouveau code OTP."
        )
    return source_path


def create_signed_pv_pdf(pv, administration, signer, signed_at):
    relative_path = signed_relative_path(pv)
    output_path = absolute_signed_path(relative_path)
    signature_statement = electronic_signature_statement(
        administration,
        signer,
        signed_at,
    )
    if pv.is_signed_by_dr:
        dr_integrity = verify_dr_signed_pv_integrity(pv)
        if not dr_integrity.is_valid:
            raise OfficialPvChangedError(
                "Le PDF signe par la DR est absent, modifie ou invalide."
            )
        result = _create_incremental_beneficiary_signature(
            dr_integrity.path,
            output_path,
            signature_statement,
            signer,
            administration,
            signed_at,
            field_name=f"BeneficiarySignature_{pv.pk}",
        )
    else:
        source_path = _official_source_path_for_signing(pv)
        result = _create_pades_signed_copy(
            source_path,
            output_path,
            signature_statement,
            signer,
            administration,
            signed_at,
            field_name=f"BeneficiarySignature_{pv.pk}",
        )
    pv.signed_pdf = relative_path
    return result


def create_dr_signed_pv_pdf(pv, delegation, signer, signed_at):
    source_path = _official_source_path_for_signing(pv)
    relative_path = dr_signed_relative_path(pv)
    result = _create_pades_signed_copy(
        source_path,
        absolute_signed_path(relative_path),
        dr_electronic_signature_statement(delegation, signer, signed_at),
        signer,
        delegation,
        signed_at,
        field_name=f"DrSignature_{pv.pk}",
        reserved_footer_slots=2,
    )
    pv.dr_signed_pdf = relative_path
    return result


def get_signed_pdf_path(pv):
    if not pv.signed_pdf:
        raise OfficialPvNotFoundError("Le PDF signe est introuvable.")

    path = absolute_signed_path(pv.signed_pdf)
    if not path.is_file():
        raise OfficialPvNotFoundError("Le PDF signe est introuvable.")
    return path


def get_dr_signed_pdf_path(pv):
    if not pv.dr_signed_pdf:
        raise OfficialPvNotFoundError("Le PDF signe par la DR est introuvable.")

    path = absolute_signed_path(pv.dr_signed_pdf)
    if not path.is_file():
        raise OfficialPvNotFoundError("Le PDF signe par la DR est introuvable.")
    return path


def verify_dr_signed_pv_integrity(pv):
    pv_hash = (pv.dr_pdf_hash_sha256 or "").strip().lower()

    try:
        signature_proof = pv.dr_signature_proof
        proof_hash = (signature_proof.pdf_hash_sha256 or "").strip().lower()
    except ObjectDoesNotExist:
        signature_proof = None
        proof_hash = ""

    if not pv.is_signed_by_dr:
        return SignedPvIntegrityResult(
            status=INTEGRITY_NOT_SIGNED,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
        )

    try:
        path = get_dr_signed_pdf_path(pv)
    except OfficialPvError:
        return SignedPvIntegrityResult(
            status=INTEGRITY_MISSING,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
        )

    if not pv_hash or not proof_hash:
        return SignedPvIntegrityResult(
            status=INTEGRITY_UNVERIFIABLE,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
            path=path,
        )

    current_hash = calculate_sha256(path).lower()
    if current_hash != pv_hash or current_hash != proof_hash:
        return SignedPvIntegrityResult(
            status=INTEGRITY_TAMPERED,
            current_hash=current_hash,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
            path=path,
            pades_error="Le hash du PDF DR ne correspond pas a la preuve.",
        )

    if not signature_proof.pades_certificate_fingerprint_sha256:
        return SignedPvIntegrityResult(
            status=INTEGRITY_UNVERIFIABLE,
            current_hash=current_hash,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
            path=path,
            pades_error="Aucune preuve PAdES DR enregistree.",
        )

    pades_result = validate_pades_signature(
        path,
        expected_field_name=signature_proof.pades_signature_field,
        expected_fingerprint_sha256=(
            signature_proof.pades_certificate_fingerprint_sha256
        ),
    )
    return SignedPvIntegrityResult(
        status=INTEGRITY_VALID if pades_result.is_valid else INTEGRITY_TAMPERED,
        current_hash=current_hash,
        pv_hash=pv_hash,
        proof_hash=proof_hash,
        path=path,
        pades_valid=pades_result.is_valid,
        pades_subject=pades_result.certificate_subject,
        pades_error=pades_result.error,
    )


def verify_signed_pv_integrity(pv):
    pv_hash = (pv.pdf_hash_sha256 or "").strip().lower()

    try:
        signature_proof = pv.signature_proof
        proof_hash = (signature_proof.pdf_hash_sha256 or "").strip().lower()
    except ObjectDoesNotExist:
        signature_proof = None
        proof_hash = ""

    if not pv.is_signed:
        return SignedPvIntegrityResult(
            status=INTEGRITY_NOT_SIGNED,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
        )

    try:
        path = get_signed_pdf_path(pv)
    except OfficialPvError:
        return SignedPvIntegrityResult(
            status=INTEGRITY_MISSING,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
        )

    if not pv_hash or not proof_hash:
        return SignedPvIntegrityResult(
            status=INTEGRITY_UNVERIFIABLE,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
            path=path,
        )

    current_hash = calculate_sha256(path).lower()
    if current_hash != pv_hash or current_hash != proof_hash:
        return SignedPvIntegrityResult(
            status=INTEGRITY_TAMPERED,
            current_hash=current_hash,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
            path=path,
            pades_error="Le hash du PDF ne correspond pas a la preuve.",
        )

    if not signature_proof or not signature_proof.pades_certificate_fingerprint_sha256:
        return SignedPvIntegrityResult(
            status=INTEGRITY_UNVERIFIABLE,
            current_hash=current_hash,
            pv_hash=pv_hash,
            proof_hash=proof_hash,
            path=path,
            pades_error="Aucune preuve PAdES enregistree.",
        )

    beneficiary_pades_result = validate_pades_signature(
        path,
        expected_field_name=signature_proof.pades_signature_field,
        expected_fingerprint_sha256=(
            signature_proof.pades_certificate_fingerprint_sha256
        ),
    )
    dr_pades_result = None
    if pv.is_signed_by_dr:
        try:
            dr_signature_proof = pv.dr_signature_proof
        except ObjectDoesNotExist:
            return SignedPvIntegrityResult(
                status=INTEGRITY_UNVERIFIABLE,
                current_hash=current_hash,
                pv_hash=pv_hash,
                proof_hash=proof_hash,
                path=path,
                pades_error="Aucune preuve PAdES DR enregistree.",
            )
        dr_pades_result = validate_pades_signature(
            path,
            expected_field_name=dr_signature_proof.pades_signature_field,
            expected_fingerprint_sha256=(
                dr_signature_proof.pades_certificate_fingerprint_sha256
            ),
            allow_later_signatures=True,
        )

    pades_is_valid = bool(
        beneficiary_pades_result.is_valid
        and (dr_pades_result is None or dr_pades_result.is_valid)
    )
    pades_errors = [
        result.error
        for result in (beneficiary_pades_result, dr_pades_result)
        if result is not None and result.error
    ]
    return SignedPvIntegrityResult(
        status=INTEGRITY_VALID if pades_is_valid else INTEGRITY_TAMPERED,
        current_hash=current_hash,
        pv_hash=pv_hash,
        proof_hash=proof_hash,
        path=path,
        pades_valid=pades_is_valid,
        pades_subject=beneficiary_pades_result.certificate_subject,
        pades_error=" ".join(pades_errors),
    )
