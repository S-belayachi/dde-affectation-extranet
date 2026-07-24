import logging
import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _

from affectations.models import DrOtpCode, PvAffectation, SignatureOtpPvDr
from affectations.services.dr_rules import can_user_sign_pv_dr
from affectations.services.otp_service import OtpDeliveryError, OtpRequestTooSoon
from affectations.services.pv_documents import create_dr_signed_pv_pdf


logger = logging.getLogger(__name__)


def generate_plain_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def send_dr_pv_otp(user, plain_code):
    if settings.PV_PRINT_OTP_TO_CONSOLE:
        logger.warning(
            "Development DR PV OTP for user=%s: %s",
            user.pk,
            plain_code,
        )
        print(f"Development DR PV OTP for user={user.pk}: {plain_code}")
        return

    recipient = user.otp_email
    if not recipient:
        raise OtpDeliveryError(
            _("La delegation ne dispose pas d'adresse e-mail OTP.")
        )

    try:
        sent = send_mail(
            subject=_("Signature DR du PV - code de verification"),
            message=(
                _("Vous avez demande la signature DR d'un PV d'affectation.\n\n")
                + _("Votre code de verification est : %(code)s\n\n")
                % {"code": plain_code}
                + _(
                    "Ce code expire dans %(minutes)s minutes et ne peut etre "
                    "utilise qu'une seule fois. "
                )
                % {"minutes": settings.PV_OTP_EXPIRY_MINUTES}
                + _("Ne le communiquez a personne.")
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as error:
        logger.exception("DR PV OTP delivery failed for user=%s", user.pk)
        raise OtpDeliveryError(
            _("Le code OTP n'a pas pu etre envoye.")
        ) from error

    if sent != 1:
        raise OtpDeliveryError(_("Le code OTP n'a pas pu etre envoye."))


def request_dr_pv_otp(user, dossier, pv):
    if not can_user_sign_pv_dr(user, dossier, pv):
        raise PermissionDenied

    now = timezone.now()
    with transaction.atomic():
        latest_otp = (
            DrOtpCode.objects.select_for_update()
            .filter(user=user, pv=pv)
            .order_by("-created_at")
            .first()
        )
        cooldown_ends_at = now - timezone.timedelta(
            seconds=settings.PV_OTP_REQUEST_COOLDOWN_SECONDS
        )
        if latest_otp and latest_otp.created_at > cooldown_ends_at:
            raise OtpRequestTooSoon(
                _("Un code vient deja d'etre demande. Attendez avant d'en demander un autre.")
            )

        DrOtpCode.objects.filter(
            user=user,
            pv=pv,
            used_at__isnull=True,
            invalidated_at__isnull=True,
        ).update(
            invalidated_at=now,
            invalidation_reason="replaced_by_new_request",
        )

        plain_code = generate_plain_otp()
        otp = DrOtpCode.objects.create(
            user=user,
            pv=pv,
            code_hash=make_password(plain_code),
            expires_at=now
            + timezone.timedelta(minutes=settings.PV_OTP_EXPIRY_MINUTES),
            max_attempts=settings.PV_OTP_MAX_ATTEMPTS,
        )
        send_dr_pv_otp(user, plain_code)

    return otp


def get_latest_usable_dr_otp(user, pv):
    return (
        DrOtpCode.objects
        .filter(
            user=user,
            pv=pv,
            used_at__isnull=True,
            invalidated_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )


def verify_dr_pv_otp(
    user,
    dossier,
    pv,
    submitted_code,
    ip_address="",
    user_agent="",
):
    with transaction.atomic():
        current_user = (
            get_user_model().objects
            .select_related("delegation")
            .get(pk=user.pk)
        )
        locked_pv = (
            PvAffectation.objects
            .select_for_update()
            .get(pk=pv.pk)
        )
        if not can_user_sign_pv_dr(current_user, dossier, locked_pv):
            raise PermissionDenied

        otp = get_latest_usable_dr_otp(current_user, locked_pv)
        if otp is None:
            return False, _("Aucun code OTP valide n'est disponible.")

        now = timezone.now()
        if otp.expires_at <= now:
            return False, _("Le code OTP a expire.")
        if otp.attempts >= otp.max_attempts:
            return False, _("Le nombre maximal de tentatives est atteint.")

        otp.attempts += 1
        if not check_password((submitted_code or "").strip(), otp.code_hash):
            otp.save(update_fields=["attempts"])
            return False, _("Code OTP incorrect.")

        otp.used_at = now
        otp.save(update_fields=["attempts", "used_at"])

        signed_result = create_dr_signed_pv_pdf(
            locked_pv,
            current_user.delegation,
            current_user,
            now,
        )
        locked_pv.delegation = current_user.delegation
        locked_pv.is_signed_by_dr = True
        locked_pv.signed_by_dr_at = now
        locked_pv.dr_pdf_hash_sha256 = signed_result.sha256
        locked_pv.save(
            update_fields=[
                "delegation",
                "dr_signed_pdf",
                "is_signed_by_dr",
                "signed_by_dr_at",
                "dr_pdf_hash_sha256",
            ]
        )

        SignatureOtpPvDr.objects.create(
            pv=locked_pv,
            user=current_user,
            delegation=current_user.delegation,
            otp_verified=True,
            signed_at=now,
            ip_address=ip_address or None,
            user_agent=user_agent or "",
            pdf_hash_sha256=signed_result.sha256,
            pades_profile=signed_result.pades.profile,
            pades_signature_field=signed_result.pades.field_name,
            pades_certificate_subject=(
                signed_result.pades.certificate_subject
            ),
            pades_certificate_serial_number=(
                signed_result.pades.certificate_serial_number
            ),
            pades_certificate_fingerprint_sha256=(
                signed_result.pades.certificate_fingerprint_sha256
            ),
        )

    return True, _("PV signe par la DR avec succes.")
