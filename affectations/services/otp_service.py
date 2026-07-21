import logging
import secrets

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from affectations.models import OtpCode, PvAffectation, SignatureOtpPv
from affectations.services.pv_generation import generate_signed_pv_pdf
from affectations.services.pv_rules import can_user_sign_pv


logger = logging.getLogger(__name__)


class OtpDeliveryError(Exception):
    """Raised when a code cannot be delivered to its intended recipient."""


class OtpRequestTooSoon(Exception):
    """Raised when a user requests another code before the cooldown ends."""


def generate_plain_otp():
    return f"{secrets.randbelow(1_000_000):06d}"


def send_pv_otp(user, plain_code):
    if settings.PV_PRINT_OTP_TO_CONSOLE:
        # This path is explicitly limited to DEBUG by settings.py.
        logger.warning("Development PV OTP for user=%s: %s", user.pk, plain_code)
        print(f"Development PV OTP for user={user.pk}: {plain_code}")
        return

    recipient = (user.email or "").strip()
    if not recipient:
        raise OtpDeliveryError(
            "Votre compte ne dispose pas d'adresse e-mail. Contactez votre administrateur organisme."
        )

    try:
        sent = send_mail(
            subject="Signature PV - code de verification",
            message=(
                "Vous avez demande la signature d'un PV d'affectation.\n\n"
                f"Votre code de verification est : {plain_code}\n\n"
                f"Ce code expire dans {settings.PV_OTP_EXPIRY_MINUTES} minutes et ne peut etre utilise qu'une seule fois. "
                "Ne le communiquez a personne."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )
    except Exception as error:
        logger.exception("PV OTP email delivery failed for user=%s", user.pk)
        raise OtpDeliveryError(
            "Le code OTP n'a pas pu etre envoye. Reessayez plus tard ou contactez la DDE."
        ) from error

    if sent != 1:
        raise OtpDeliveryError(
            "Le code OTP n'a pas pu etre envoye. Reessayez plus tard ou contactez la DDE."
        )


def request_pv_otp(user, dossier, pv):
    if not can_user_sign_pv(user, dossier, pv):
        raise PermissionDenied

    now = timezone.now()
    with transaction.atomic():
        latest_otp = (
            OtpCode.objects.select_for_update()
            .filter(user=user, pv=pv)
            .order_by("-created_at")
            .first()
        )
        cooldown_ends_at = now - timezone.timedelta(
            seconds=settings.PV_OTP_REQUEST_COOLDOWN_SECONDS
        )
        if latest_otp and latest_otp.created_at > cooldown_ends_at:
            raise OtpRequestTooSoon(
                "Un code vient deja d'etre demande. Attendez avant d'en demander un autre."
            )

        OtpCode.objects.filter(
            user=user,
            pv=pv,
            used_at__isnull=True,
            invalidated_at__isnull=True,
        ).update(invalidated_at=now, invalidation_reason="replaced_by_new_request")

        plain_code = generate_plain_otp()
        otp = OtpCode.objects.create(
            user=user,
            pv=pv,
            code_hash=make_password(plain_code),
            expires_at=now + timezone.timedelta(minutes=settings.PV_OTP_EXPIRY_MINUTES),
            max_attempts=settings.PV_OTP_MAX_ATTEMPTS,
        )
        send_pv_otp(user, plain_code)

    return otp


def get_latest_usable_otp(user, pv):
    return (
        OtpCode.objects
        .filter(
            user=user,
            pv=pv,
            used_at__isnull=True,
            invalidated_at__isnull=True,
        )
        .order_by("-created_at")
        .first()
    )


def verify_pv_otp(user, dossier, pv, submitted_code, ip_address="", user_agent=""):
    with transaction.atomic():
        current_user = (
            get_user_model().objects.select_related("administration").get(pk=user.pk)
        )
        pv = PvAffectation.objects.select_for_update().get(pk=pv.pk)
        if not can_user_sign_pv(current_user, dossier, pv):
            raise PermissionDenied

        otp = get_latest_usable_otp(current_user, pv)
        if not otp:
            return False, "Aucun code OTP valide n'a ete demande."

        now = timezone.now()
        if otp.expires_at <= now:
            return False, "Le code OTP a expire."

        if otp.attempts >= otp.max_attempts:
            return False, "Le nombre maximum de tentatives est atteint."

        otp.attempts += 1
        if not check_password(submitted_code, otp.code_hash):
            otp.save(update_fields=["attempts"])
            return False, "Code OTP incorrect."

        otp.used_at = now
        otp.save(update_fields=["attempts", "used_at"])

        pdf_hash = generate_signed_pv_pdf(pv, current_user.administration)

        pv.is_signed = True
        pv.signed_at = now
        pv.pdf_hash_sha256 = pdf_hash
        pv.save(update_fields=["is_signed", "signed_at", "pdf_hash_sha256"])

        SignatureOtpPv.objects.create(
            pv=pv,
            user=current_user,
            administration=current_user.administration,
            otp_verified=True,
            signed_at=now,
            ip_address=ip_address or None,
            user_agent=user_agent or "",
            pdf_hash_sha256=pdf_hash,
        )

    return True, "PV signe avec succes."
