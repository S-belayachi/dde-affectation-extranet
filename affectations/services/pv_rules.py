import hashlib

from affectations.models import PvAffectation


PV_READY_STATUSES = {"Signé par DR"}


def normalize_key_part(value):
    value = "" if value is None else str(value)
    return " ".join(value.strip().split())


def build_pv_group_source(dossier):
    pv_reference = normalize_key_part(dossier.numero_pv) or f"import-{dossier.import_id}"
    return "|".join(
        [
            normalize_key_part(dossier.administration_beneficiaire),
            normalize_key_part(dossier.num_dossier),
            pv_reference,
        ]
    )


def build_pv_key(dossier):
    return hashlib.sha256(build_pv_group_source(dossier).encode("utf-8")).hexdigest()


def is_dossier_at_pv_signature_step(dossier):
    return dossier.statut_pv in PV_READY_STATUSES


def user_matches_dossier_administration(user, dossier):
    return bool(
        getattr(user, "administration_id", None)
        and user.administration.nom == dossier.administration_beneficiaire
    )


def can_user_access_dossier(user, dossier):
    return bool(
        user.is_authenticated
        and user.can_access_extranet
        and user_matches_dossier_administration(user, dossier)
    )


def can_user_access_pv(user, dossier, pv=None):
    if not can_user_sign_pv(user, dossier, pv):
        return False
    return True


def can_user_sign_pv(user, dossier, pv=None):
    if not (
        user.is_authenticated
        and user.can_access_extranet
        and user.can_sign_pv
        and user_matches_dossier_administration(user, dossier)
        and is_dossier_at_pv_signature_step(dossier)
    ):
        return False

    if pv is None:
        pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()

    return not (pv and pv.is_signed)


def get_pv_status(dossier):
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if pv and pv.is_signed:
        return "signed"
    if is_dossier_at_pv_signature_step(dossier):
        return "ready_for_beneficiary_signature"
    return "not_ready"
