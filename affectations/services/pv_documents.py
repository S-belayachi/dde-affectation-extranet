import hashlib
import re
import tempfile
from pathlib import Path

import fitz
from django.conf import settings
from django.utils import timezone

from affectations.models import PvAffectation
from affectations.services.pv_rules import build_pv_key


ELECTRONIC_SIGNATURE_PREFIX = "Signé électroniquement par "


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


def electronic_signature_statement(administration):
    return f"{ELECTRONIC_SIGNATURE_PREFIX}{administration.nom}"


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


def create_signed_pv_pdf(pv, administration):
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
        footer = fitz.Rect(
            page.rect.x0 + 36,
            page.rect.y1 - 30,
            page.rect.x1 - 36,
            page.rect.y1 - 10,
        )
        remaining_height = page.insert_textbox(
            footer,
            electronic_signature_statement(administration),
            fontname="helv",
            fontsize=8,
            align=fitz.TEXT_ALIGN_CENTER,
            color=(0, 0, 0),
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
