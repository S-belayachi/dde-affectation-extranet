from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _

from accounts.decorators import capability_required, role_required

from .models import (
    AdministrationBeneficiaire,
    PvAffectation,
    TableFaitAffectationDatalab,
)
from .services.dr_otp_service import request_dr_pv_otp, verify_dr_pv_otp
from .services.otp_service import (
    OtpDeliveryError,
    OtpRequestTooSoon,
    request_pv_otp,
    verify_pv_otp,
)
from .services.dr_rules import (
    DR_READY_STATUSES,
    can_user_access_dr_dossier,
    can_user_sign_pv_dr,
)
from .services.pv_documents import (
    INTEGRITY_MISSING,
    OfficialPvError,
    get_dr_signed_pdf_path,
    retrieve_official_pv,
    verify_dr_signed_pv_integrity,
    verify_signed_pv_integrity,
)
from .services.pv_rules import (
    PV_READY_STATUSES,
    build_pv_key,
    can_user_access_dossier,
    can_user_access_pv,
    can_user_sign_pv,
    get_pv_status,
)


@capability_required("can_consult_dr_dossiers")
def delegation_dossier_list(request):
    delegation = request.user.delegation
    dr_signed_import_ids = PvAffectation.objects.filter(
        delegation=delegation,
        is_signed_by_dr=True,
    ).values("source_import_id")
    dossiers = (
        TableFaitAffectationDatalab.objects
        .filter(
            delegation=delegation.nom,
            statut_pv__in=DR_READY_STATUSES,
        )
        .exclude(import_id__in=dr_signed_import_ids)
        .order_by("num_dossier", "import_id")
    )
    return render(
        request,
        "affectations/delegation_dossier_list.html",
        {
            "delegation": delegation,
            "dossiers": dossiers,
        },
    )


@capability_required("can_consult_dr_dossiers")
def delegation_dossier_detail(request, import_id):
    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_access_dr_dossier(request.user, dossier, pv):
        raise PermissionDenied

    can_sign = can_user_sign_pv_dr(request.user, dossier, pv)
    official_pv_available = False
    official_pv_error = ""
    if can_sign:
        try:
            pv, _source_path = _prepare_dr_pv(
                dossier,
                request.user.delegation,
            )
            official_pv_available = True
        except OfficialPvError as error:
            official_pv_error = str(error)

    return render(
        request,
        "affectations/delegation_dossier_detail.html",
        {
            "dossier": dossier,
            "pv": pv,
            "can_sign_pv_dr": can_sign,
            "official_pv_available": official_pv_available,
            "official_pv_error": official_pv_error,
            "expected_official_filename": f"{dossier.import_id}.pdf",
        },
    )


def _prepare_dr_pv(dossier, delegation):
    administration = AdministrationBeneficiaire.objects.filter(
        nom=dossier.administration_beneficiaire
    ).first()
    if administration is None:
        raise OfficialPvError(
            "L'administration beneficiaire du dossier est introuvable."
        )
    pv, source_path = retrieve_official_pv(dossier, administration)
    if pv.delegation_id and pv.delegation_id != delegation.pk:
        raise OfficialPvError("Ce PV est rattache a une autre delegation.")
    if not pv.delegation_id:
        pv.delegation = delegation
        pv.save(update_fields=["delegation"])
    return pv, source_path


@capability_required("can_consult_dr_dossiers")
def delegation_pv_pdf(request, import_id):
    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_sign_pv_dr(request.user, dossier, pv):
        raise PermissionDenied

    try:
        pv, pdf_path = _prepare_dr_pv(dossier, request.user.delegation)
    except OfficialPvError as error:
        messages.error(request, str(error))
        return redirect(
            "affectations:delegation_dossier_detail",
            import_id=import_id,
        )
    response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pv-dr-{pv.id}.pdf"'
    return response


@capability_required("can_consult_dr_dossiers")
def delegation_pv_otp_request(request, import_id):
    if request.method != "POST":
        return redirect(
            "affectations:delegation_dossier_detail",
            import_id=import_id,
        )

    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_sign_pv_dr(request.user, dossier, pv):
        raise PermissionDenied

    try:
        pv, _source_path = _prepare_dr_pv(dossier, request.user.delegation)
        request_dr_pv_otp(request.user, dossier, pv)
    except (OfficialPvError, OtpDeliveryError, OtpRequestTooSoon) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, _("Code OTP envoye a votre adresse e-mail."))
    return redirect(
        "affectations:delegation_dossier_detail",
        import_id=import_id,
    )


@capability_required("can_consult_dr_dossiers")
def delegation_pv_otp_verify(request, import_id):
    if request.method != "POST":
        return redirect(
            "affectations:delegation_dossier_detail",
            import_id=import_id,
        )

    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_sign_pv_dr(request.user, dossier, pv):
        raise PermissionDenied
    if pv is None:
        messages.error(request, _("Aucun PV officiel n'a ete prepare pour signature."))
        return redirect(
            "affectations:delegation_dossier_detail",
            import_id=import_id,
        )

    try:
        success, message = verify_dr_pv_otp(
            request.user,
            dossier,
            pv,
            request.POST.get("otp_code", ""),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except OfficialPvError as error:
        success, message = False, str(error)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)
    return redirect(
        "affectations:delegation_dossier_detail",
        import_id=import_id,
    )


@capability_required("can_consult_dossiers")
def dossier_list(request):
    administration = request.user.administration
    dossiers = TableFaitAffectationDatalab.objects.none()

    if request.user.can_consult_dossiers:
        dossiers = (
            TableFaitAffectationDatalab.objects
            .filter(administration_beneficiaire=administration.nom)
            .order_by("num_dossier", "import_id")
        )
        if request.user.is_signataire:
            dr_ready_import_ids = PvAffectation.objects.filter(
                administration=administration,
                is_signed_by_dr=True,
                is_signed=False,
            ).values("source_import_id")
            dossiers = dossiers.filter(
                Q(statut_pv__in=PV_READY_STATUSES)
                | Q(import_id__in=dr_ready_import_ids)
            )

    context = {
        "administration": administration,
        "dossiers": dossiers,
    }
    return render(request, "affectations/dossier_list.html", context)


@capability_required("can_consult_dossiers")
def dossier_detail(request, import_id):
    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    if not can_user_access_dossier(request.user, dossier):
        raise PermissionDenied
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if (
        request.user.is_signataire
        and not can_user_sign_pv(request.user, dossier, pv)
        and not (pv and pv.is_signed)
    ):
        raise PermissionDenied

    can_sign = can_user_sign_pv(request.user, dossier, pv)

    context = {
        "dossier": dossier,
        "pv": pv,
        "pv_status": get_pv_status(dossier),
        "can_sign_pv": can_sign,
        "can_access_pv": can_user_access_pv(request.user, dossier, pv),
    }
    return render(request, "affectations/dossier_detail.html", context)


@capability_required("can_consult_dossiers")
def pv_pdf(request, import_id):
    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_access_pv(request.user, dossier, pv):
        raise PermissionDenied

    try:
        if pv and pv.is_signed_by_dr:
            integrity = verify_dr_signed_pv_integrity(pv)
            if not integrity.is_valid:
                raise PermissionDenied(
                    _("L'integrite du PDF signe par la DR est compromise.")
                )
            pdf_path = get_dr_signed_pdf_path(pv)
        else:
            pv, pdf_path = retrieve_official_pv(
                dossier,
                request.user.administration,
            )
    except OfficialPvError as error:
        raise Http404(_("PV officiel indisponible.")) from error
    response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pv-{pv.id}.pdf"'
    return response


@role_required("admin_dde")
def dde_signed_pv_pdf(request, pv_id):
    """Allow internal DDE supervision of the signed PDF only."""
    pv = get_object_or_404(PvAffectation, pk=pv_id, is_signed=True)
    integrity = verify_signed_pv_integrity(pv)
    if integrity.status == INTEGRITY_MISSING:
        raise Http404(_("PDF signe indisponible."))
    if not integrity.is_valid:
        raise PermissionDenied(
            _("L'integrite du PDF signe est compromise. Acces bloque.")
        )

    response = FileResponse(open(integrity.path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pv-signe-{pv.id}.pdf"'
    return response


@capability_required("can_consult_dossiers")
def pv_otp_request(request, import_id):
    if request.method != "POST":
        return redirect("affectations:dossier_detail", import_id=import_id)

    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_sign_pv(request.user, dossier, pv):
        raise PermissionDenied

    try:
        pv, _source_path = retrieve_official_pv(dossier, request.user.administration)
        request_pv_otp(request.user, dossier, pv)
    except (OfficialPvError, OtpDeliveryError, OtpRequestTooSoon) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, _("Code OTP envoye a votre adresse e-mail."))
    return redirect("affectations:dossier_detail", import_id=import_id)


@capability_required("can_consult_dossiers")
def pv_otp_verify(request, import_id):
    if request.method != "POST":
        return redirect("affectations:dossier_detail", import_id=import_id)

    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_sign_pv(request.user, dossier, pv):
        raise PermissionDenied
    if pv is None:
        messages.error(request, _("Aucun PV officiel n'a ete prepare pour signature."))
        return redirect("affectations:dossier_detail", import_id=import_id)

    try:
        success, message = verify_pv_otp(
            request.user,
            dossier,
            pv,
            request.POST.get("otp_code", ""),
            ip_address=get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
    except OfficialPvError as error:
        success, message = False, str(error)

    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect("affectations:dossier_detail", import_id=import_id)


def get_client_ip(request):
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
