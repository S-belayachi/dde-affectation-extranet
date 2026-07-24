from affectations.models import PvAffectation
from affectations.services.pv_rules import build_pv_key


DR_READY_STATUSES = {"Validé"}


def get_dr_pv(dossier):
    return PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()


def user_matches_dossier_delegation(user, dossier):
    return bool(
        getattr(user, "delegation_id", None)
        and user.delegation.nom == dossier.delegation
    )


def can_user_access_dr_dossier(user, dossier, pv=None):
    if pv is None:
        pv = get_dr_pv(dossier)
    return bool(
        user.is_authenticated
        and user.can_consult_dr_dossiers
        and user_matches_dossier_delegation(user, dossier)
        and (
            dossier.statut_pv in DR_READY_STATUSES
            or (pv and pv.is_signed_by_dr)
        )
    )


def can_user_sign_pv_dr(user, dossier, pv=None):
    if pv is None:
        pv = get_dr_pv(dossier)
    return bool(
        user.is_authenticated
        and user.can_sign_pv_dr
        and user_matches_dossier_delegation(user, dossier)
        and dossier.statut_pv in DR_READY_STATUSES
        and not (pv and pv.is_signed_by_dr)
    )
