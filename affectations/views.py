from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.decorators import capability_required, role_required

from .models import PvAffectation, TableFaitAffectationDatalab
from .services.otp_service import (
    OtpDeliveryError,
    OtpRequestTooSoon,
    request_pv_otp,
    verify_pv_otp,
)
from .services.pv_generation import absolute_generated_path, generate_pv_pdf
from .services.pv_rules import (
    build_pv_key,
    can_user_access_dossier,
    can_user_access_pv,
    can_user_sign_pv,
    get_pv_status,
)


@capability_required("can_access_extranet")
def dossier_list(request):
    administration = request.user.administration
    dossiers = TableFaitAffectationDatalab.objects.none()

    if request.user.can_consult_dossiers:
        dossiers = (
            TableFaitAffectationDatalab.objects
            .filter(administration_beneficiaire=administration.nom)
            .order_by("num_dossier", "import_id")
        )

    context = {
        "administration": administration,
        "dossiers": dossiers,
    }
    return render(request, "affectations/dossier_list.html", context)


@capability_required("can_access_extranet")
def dossier_detail(request, import_id):
    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    if not can_user_access_dossier(request.user, dossier):
        raise PermissionDenied

    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    can_sign = can_user_sign_pv(request.user, dossier, pv)

    context = {
        "dossier": dossier,
        "pv": pv,
        "pv_status": get_pv_status(dossier),
        "can_sign_pv": can_sign,
        "can_access_pv": can_user_access_pv(request.user, dossier, pv),
    }
    return render(request, "affectations/dossier_detail.html", context)


@capability_required("can_access_extranet")
def pv_pdf(request, import_id):
    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_access_pv(request.user, dossier, pv):
        raise PermissionDenied

    pv = generate_pv_pdf(dossier, request.user.administration)
    pdf_path = absolute_generated_path(pv.generated_pdf)
    response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pv-{pv.id}.pdf"'
    return response


@role_required("admin_dde")
def dde_signed_pv_pdf(request, pv_id):
    """Allow internal DDE supervision of the signed PDF only."""
    pv = get_object_or_404(PvAffectation, pk=pv_id, is_signed=True)
    if not pv.generated_pdf:
        raise PermissionDenied

    pdf_path = absolute_generated_path(pv.generated_pdf)
    if not pdf_path.exists():
        raise PermissionDenied

    response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="pv-signe-{pv.id}.pdf"'
    return response


@capability_required("can_access_extranet")
def pv_otp_request(request, import_id):
    if request.method != "POST":
        return redirect("affectations:dossier_detail", import_id=import_id)

    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_sign_pv(request.user, dossier, pv):
        raise PermissionDenied

    pv = generate_pv_pdf(dossier, request.user.administration)
    try:
        request_pv_otp(request.user, dossier, pv)
    except (OtpDeliveryError, OtpRequestTooSoon) as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Code OTP envoye a votre adresse e-mail.")
    return redirect("affectations:dossier_detail", import_id=import_id)


@capability_required("can_access_extranet")
def pv_otp_verify(request, import_id):
    if request.method != "POST":
        return redirect("affectations:dossier_detail", import_id=import_id)

    dossier = get_object_or_404(TableFaitAffectationDatalab, import_id=import_id)
    pv = PvAffectation.objects.filter(pv_key=build_pv_key(dossier)).first()
    if not can_user_sign_pv(request.user, dossier, pv):
        raise PermissionDenied

    pv = generate_pv_pdf(dossier, request.user.administration)
    success, message = verify_pv_otp(
        request.user,
        dossier,
        pv,
        request.POST.get("otp_code", ""),
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", ""),
    )

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
