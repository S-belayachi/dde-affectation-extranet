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
        f"بتاريخ {local_signed_at:%d/%m/%Y}"
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


def create_signed_pv_pdf(pv, administration, signer, signed_at):
    if not pv.source_filename or not pv.source_pdf_hash_sha256:
        raise OfficialPvError("Le PV officiel doit etre recupere avant signature.")

    source_path = safe_path(settings.AMLACS_PV_OFFICIAL_ROOT, pv.source_filename)
    if not source_path.is_file():
        raise OfficialPvNotFoundError("Le PV officiel AMLACS est introuvable.")
    if calculate_sha256(source_path) != pv.source_pdf_hash_sha256:
        raise OfficialPvChangedError(
            "Le PV officiel a change. Demandez un nouveau code OTP."
        )

    relative_path = signed_relative_path(pv)
    output_path = absolute_signed_path(relative_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = None
    document = None

    try:
        document = fitz.open(source_path)
        if document.page_count == 0:
            raise OfficialPvError("Le PDF officiel est vide.")

        page = document[document.page_count - 1]
        original_page_height = page.rect.height
        media_box = page.mediabox
        page.set_mediabox(
            fitz.Rect(
                media_box.x0,
                media_box.y0 - ELECTRONIC_SIGNATURE_FOOTER_HEIGHT,
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
            page_rect.y1 - 8,
        )
        arabic_font_path = Path(settings.PV_ARABIC_FONT_PATH).resolve()
        if not arabic_font_path.is_file():
            raise OfficialPvError(
                "La police arabe du pied de page est introuvable."
            )
        font_archive = fitz.Archive(arabic_font_path.parent)
        signature_date = timezone.localtime(signed_at).strftime("%d/%m/%Y")
        signature_statement = escape(
            electronic_signature_statement(administration, signer, signed_at)
        ).replace(
            escape(signature_date),
            f'<span class="signature-date" dir="ltr">{signature_date}</span>',
            1,
        )
        html = (
            '<div class="signature" dir="rtl" lang="ar">'
            f"{signature_statement}</div>"
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
            .signature-date {{
                direction: ltr;
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
            temporary_path = Path(temporary_file.name)
        document.save(temporary_path, garbage=4, deflate=True)
        temporary_path.replace(output_path)
    except fitz.FileDataError as error:
        raise OfficialPvError("Le PDF officiel AMLACS est invalide.") from error
    finally:
        if document is not None:
            document.close()
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()

    pv.signed_pdf = relative_path
    return calculate_sha256(output_path)


def get_signed_pdf_path(pv):
    if not pv.signed_pdf:
        raise OfficialPvNotFoundError("Le PDF signe est introuvable.")

    path = absolute_signed_path(pv.signed_pdf)
    if not path.is_file():
        raise OfficialPvNotFoundError("Le PDF signe est introuvable.")
    return path


def verify_signed_pv_integrity(pv):
    pv_hash = (pv.pdf_hash_sha256 or "").strip().lower()

    try:
        proof_hash = (pv.signature_proof.pdf_hash_sha256 or "").strip().lower()
    except ObjectDoesNotExist:
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
    status = (
        INTEGRITY_VALID
        if current_hash == pv_hash == proof_hash
        else INTEGRITY_TAMPERED
    )
    return SignedPvIntegrityResult(
        status=status,
        current_hash=current_hash,
        pv_hash=pv_hash,
        proof_hash=proof_hash,
        path=path,
    )
