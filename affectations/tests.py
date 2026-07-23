from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core import mail
from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
import fitz
import tempfile
import shutil
from pathlib import Path

from .models import (
    AdministrationBeneficiaire,
    OtpCode,
    PvAffectation,
    SignatureOtpPv,
    TableFaitAffectationDatalab,
)
from .services.pv_documents import (
    INTEGRITY_TAMPERED,
    INTEGRITY_VALID,
    calculate_sha256,
    electronic_signature_statement,
    get_signed_pdf_path,
    retrieve_official_pv,
    verify_signed_pv_integrity,
)
from .services.pv_rules import PV_READY_STATUSES


User = get_user_model()


class DossierListAccessTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TableFaitAffectationDatalab)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(TableFaitAffectationDatalab)
        super().tearDownClass()

    def setUp(self):
        self.education = AdministrationBeneficiaire.objects.create(
            nom="Education Nationale"
        )
        self.sports = AdministrationBeneficiaire.objects.create(
            nom="Jeunesse Et Sports"
        )
        self.education_user = User.objects.create_user(
            username="education_user",
            password="StrongPass123!",
            role=User.ROLE_CONSULTATION,
            administration=self.education,
        )
        self.education_signataire = User.objects.create_user(
            username="education_signataire",
            password="StrongPass123!",
            role=User.ROLE_SIGNATAIRE,
            administration=self.education,
            peut_signer=True,
        )
        self.admin_dde = User.objects.create_user(
            username="admin_dde",
            password="StrongPass123!",
            role=User.ROLE_ADMIN_DDE,
            is_staff=True,
            is_superuser=True,
        )
        TableFaitAffectationDatalab.objects.create(
            num_dossier="EDU-001",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Ecole primaire",
            statut_dossier="PV etabli",
            statut_pv="Valide",
        )
        TableFaitAffectationDatalab.objects.create(
            num_dossier="SPORT-001",
            administration_beneficiaire="Jeunesse Et Sports",
            denomination_projet="Complexe sportif",
            statut_dossier="En cours",
            statut_pv="",
        )
        self.ready_education_dossier = TableFaitAffectationDatalab.objects.create(
            num_dossier="EDU-PV-READY",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Ecole prete a signer",
            statut_dossier="PV etabli",
            statut_pv=next(iter(PV_READY_STATUSES)),
        )

    def test_dossier_list_requires_login(self):
        response = self.client.get(reverse("affectations:dossier_list"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/login/?next=/dossiers/")

    def test_user_sees_only_dossiers_for_own_administration(self):
        self.client.force_login(self.education_user)

        response = self.client.get(reverse("affectations:dossier_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EDU-001")
        self.assertContains(response, "Ecole primaire")
        self.assertNotContains(response, "SPORT-001")
        self.assertNotContains(response, "Complexe sportif")

    def test_admin_dde_cannot_access_extranet_dossier_list(self):
        self.client.force_login(self.admin_dde)

        response = self.client.get(reverse("affectations:dossier_list"))

        self.assertEqual(response.status_code, 403)

    def test_signataire_sees_only_ready_for_signature_dossiers(self):
        self.client.force_login(self.education_signataire)

        response = self.client.get(reverse("affectations:dossier_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "EDU-PV-READY")
        self.assertNotContains(response, "EDU-001")

class PvAffectationFlowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TableFaitAffectationDatalab)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(TableFaitAffectationDatalab)
        super().tearDownClass()

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))
        self.document_root = Path(self.tmpdir) / "pv_documents"
        self.override = override_settings(
            PV_PRINT_OTP_TO_CONSOLE=False,
            EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
            DEFAULT_FROM_EMAIL="pv-otp@example.test",
            PV_DOCUMENT_ROOT=self.document_root,
            AMLACS_PV_OFFICIAL_ROOT=self.document_root / "official",
            SIGNED_PV_ROOT=self.document_root / "signed",
        )
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.education = AdministrationBeneficiaire.objects.create(
            nom="Education Nationale"
        )
        self.sports = AdministrationBeneficiaire.objects.create(
            nom="Jeunesse Et Sports"
        )
        self.consultation_user = User.objects.create_user(
            username="consultation",
            password="StrongPass123!",
            role=User.ROLE_CONSULTATION,
            administration=self.education,
        )
        self.signataire = User.objects.create_user(
            username="signataire",
            password="StrongPass123!",
            email="signataire@example.test",
            role=User.ROLE_SIGNATAIRE,
            administration=self.education,
            peut_signer=True,
        )
        self.other_signataire = User.objects.create_user(
            username="other_signataire",
            password="StrongPass123!",
            role=User.ROLE_SIGNATAIRE,
            administration=self.sports,
            peut_signer=True,
        )
        self.admin_dde = User.objects.create_user(
            username="pv_admin_dde",
            password="StrongPass123!",
            role=User.ROLE_ADMIN_DDE,
            is_staff=True,
            is_superuser=True,
        )

        self.ready_dossier = TableFaitAffectationDatalab.objects.create(
            num_dossier="EDU-PV-001",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Ecole primaire",
            numero_pv="PV-001",
            type_pv="PV d'affectation",
            statut_pv="Signé par DR",
        )
        self.ready_duplicate = TableFaitAffectationDatalab.objects.create(
            num_dossier="EDU-PV-001",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Ecole primaire - ligne duplicate",
            numero_pv="PV-001",
            type_pv="PV d'affectation",
            statut_pv="Signé par DR",
        )
        self.not_ready_dossier = TableFaitAffectationDatalab.objects.create(
            num_dossier="EDU-PV-002",
            administration_beneficiaire="Education Nationale",
            denomination_projet="College",
            numero_pv="PV-002",
            statut_pv="Validé",
        )

        for dossier in (
            self.ready_dossier,
            self.ready_duplicate,
            self.not_ready_dossier,
        ):
            self.create_official_pdf(dossier)

    def create_official_pdf(self, dossier):
        path = self.document_root / "official" / f"{dossier.import_id}.pdf"
        path.parent.mkdir(parents=True, exist_ok=True)
        document = fitz.open()
        page = document.new_page()
        page.insert_text(
            (72, 72),
            f"PV officiel AMLACS {dossier.num_dossier} {dossier.numero_pv}",
        )
        document.save(path)
        document.close()

    def test_signataire_cannot_open_dossier_when_status_is_not_ready(self):
        self.client.force_login(self.signataire)

        response = self.client.get(
            reverse("affectations:dossier_detail", args=[self.not_ready_dossier.import_id])
        )

        self.assertEqual(response.status_code, 403)

    def test_pv_buttons_hidden_for_consultation_user(self):
        self.client.force_login(self.consultation_user)

        response = self.client.get(
            reverse("affectations:dossier_detail", args=[self.ready_dossier.import_id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Consulter le PV")
        self.assertNotContains(response, "Signer par OTP")

    def test_pv_buttons_shown_for_authorized_signataire(self):
        self.client.force_login(self.signataire)

        response = self.client.get(
            reverse("affectations:dossier_detail", args=[self.ready_dossier.import_id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Consulter le PV")
        self.assertContains(response, "Signer par OTP")

    def test_other_administration_cannot_access_dossier_or_pv(self):
        self.client.force_login(self.other_signataire)

        detail_response = self.client.get(
            reverse("affectations:dossier_detail", args=[self.ready_dossier.import_id])
        )
        pdf_response = self.client.get(
            reverse("affectations:pv_pdf", args=[self.ready_dossier.import_id])
        )

        self.assertEqual(detail_response.status_code, 403)
        self.assertEqual(pdf_response.status_code, 403)

    def test_admin_dde_cannot_access_extranet_pv_views(self):
        self.client.force_login(self.admin_dde)

        response = self.client.get(
            reverse("affectations:pv_pdf", args=[self.ready_dossier.import_id])
        )

        self.assertEqual(response.status_code, 403)

    def test_pdf_view_is_protected_and_does_not_expose_file_path(self):
        self.client.force_login(self.signataire)

        response = self.client.get(
            reverse("affectations:pv_pdf", args=[self.ready_dossier.import_id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertNotIn(str(self.document_root), response["Content-Disposition"])
        pv = PvAffectation.objects.get()
        self.assertEqual(pv.source_filename, f"{self.ready_dossier.import_id}.pdf")
        self.assertTrue(pv.source_pdf_hash_sha256)

    def test_grouped_dossier_rows_share_one_pv_record(self):
        retrieve_official_pv(self.ready_dossier, self.education)
        retrieve_official_pv(self.ready_duplicate, self.education)

        self.assertEqual(PvAffectation.objects.count(), 1)

    def test_otp_request_creates_hashed_code_only(self):
        self.client.force_login(self.signataire)

        response = self.client.post(
            reverse("affectations:pv_otp_request", args=[self.ready_dossier.import_id])
        )
        otp = OtpCode.objects.get()

        self.assertEqual(response.status_code, 302)
        self.assertNotRegex(otp.code_hash, r"^\d{6}$")
        self.assertEqual(otp.attempts, 0)

    def test_otp_request_sends_email_only_to_the_signataire(self):
        self.client.force_login(self.signataire)

        response = self.client.post(
            reverse("affectations:pv_otp_request", args=[self.ready_dossier.import_id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.signataire.email])
        self.assertIn("code de verification", mail.outbox[0].subject)

    def test_new_otp_request_invalidates_the_previous_code(self):
        self.client.force_login(self.signataire)

        with override_settings(PV_OTP_REQUEST_COOLDOWN_SECONDS=0):
            self.client.post(
                reverse("affectations:pv_otp_request", args=[self.ready_dossier.import_id])
            )
            self.client.post(
                reverse("affectations:pv_otp_request", args=[self.ready_dossier.import_id])
            )

        first_otp, second_otp = OtpCode.objects.order_by("created_at")
        self.assertIsNotNone(first_otp.invalidated_at)
        self.assertEqual(first_otp.invalidation_reason, "replaced_by_new_request")
        self.assertIsNone(second_otp.invalidated_at)

    def test_wrong_otp_increments_attempts(self):
        pv, _source_path = retrieve_official_pv(self.ready_dossier, self.education)
        OtpCode.objects.create(
            user=self.signataire,
            pv=pv,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        self.client.force_login(self.signataire)

        response = self.client.post(
            reverse("affectations:pv_otp_verify", args=[self.ready_dossier.import_id]),
            {"otp_code": "000000"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(OtpCode.objects.get().attempts, 1)
        pv.refresh_from_db()
        self.assertFalse(pv.is_signed)

    def test_expired_otp_fails(self):
        pv, _source_path = retrieve_official_pv(self.ready_dossier, self.education)
        OtpCode.objects.create(
            user=self.signataire,
            pv=pv,
            code_hash=make_password("123456"),
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        self.client.force_login(self.signataire)

        response = self.client.post(
            reverse("affectations:pv_otp_verify", args=[self.ready_dossier.import_id]),
            {"otp_code": "123456"},
        )

        self.assertEqual(response.status_code, 302)
        pv.refresh_from_db()
        self.assertFalse(pv.is_signed)

    def test_used_otp_fails(self):
        pv, _source_path = retrieve_official_pv(self.ready_dossier, self.education)
        OtpCode.objects.create(
            user=self.signataire,
            pv=pv,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
            used_at=timezone.now(),
        )
        self.client.force_login(self.signataire)

        response = self.client.post(
            reverse("affectations:pv_otp_verify", args=[self.ready_dossier.import_id]),
            {"otp_code": "123456"},
        )

        self.assertEqual(response.status_code, 302)
        pv.refresh_from_db()
        self.assertFalse(pv.is_signed)

    def test_changed_official_pdf_cannot_be_signed_with_an_existing_otp(self):
        pv, source_path = retrieve_official_pv(self.ready_dossier, self.education)
        OtpCode.objects.create(
            user=self.signataire,
            pv=pv,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        source_path.write_bytes(b"changed-after-otp-request")
        self.client.force_login(self.signataire)

        response = self.client.post(
            reverse("affectations:pv_otp_verify", args=[self.ready_dossier.import_id]),
            {"otp_code": "123456"},
        )

        pv.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertFalse(pv.is_signed)
        self.assertIsNone(OtpCode.objects.get().used_at)
        self.assertEqual(SignatureOtpPv.objects.count(), 0)

    def test_successful_otp_signature_marks_pv_signed_and_blocks_pdf(self):
        pv, _source_path = retrieve_official_pv(self.ready_dossier, self.education)
        source_hash_before_signature = calculate_sha256(_source_path)
        source_document = fitz.open(_source_path)
        source_page_height = source_document[-1].rect.height
        source_text_position = source_document[-1].search_for(
            "PV officiel AMLACS"
        )[0]
        source_document.close()
        self.signataire.first_name = "Souhayl"
        self.signataire.last_name = "Belayachi"
        self.signataire.prenom_ar = "سهيل"
        self.signataire.nom_ar = "بلاياشي"
        self.signataire.fonction = "Responsable habilité"
        self.signataire.save(
            update_fields=[
                "first_name",
                "last_name",
                "prenom_ar",
                "nom_ar",
                "fonction",
            ]
        )
        self.education.nom_ar = "وزارة التربية الوطنية"
        self.education.save(update_fields=["nom_ar"])
        OtpCode.objects.create(
            user=self.signataire,
            pv=pv,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        self.client.force_login(self.signataire)

        response = self.client.post(
            reverse("affectations:pv_otp_verify", args=[self.ready_dossier.import_id]),
            {"otp_code": "123456"},
            HTTP_USER_AGENT="Test agent",
        )
        pv.refresh_from_db()
        pdf_response = self.client.get(
            reverse("affectations:pv_pdf", args=[self.ready_dossier.import_id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(pv.is_signed)
        self.assertIsNotNone(pv.signed_at)
        self.assertTrue(pv.signed_pdf.startswith("signed"))
        self.assertEqual(calculate_sha256(_source_path), source_hash_before_signature)
        self.assertEqual(SignatureOtpPv.objects.count(), 1)
        signature_proof = SignatureOtpPv.objects.get()
        self.assertEqual(signature_proof.user_agent, "Test agent")
        self.assertEqual(signature_proof.signed_at, pv.signed_at)
        self.assertEqual(signature_proof.pdf_hash_sha256, pv.pdf_hash_sha256)
        self.assertEqual(verify_signed_pv_integrity(pv).status, INTEGRITY_VALID)
        signed_document = fitz.open(get_signed_pdf_path(pv))
        signed_page_height = signed_document[-1].rect.height
        signed_text_position = signed_document[-1].search_for(
            "PV officiel AMLACS"
        )[0]
        footer_text = " ".join(
            signed_document[-1]
            .get_text(
                clip=fitz.Rect(
                    0,
                    source_page_height,
                    signed_document[-1].rect.width,
                    signed_document[-1].rect.height,
                )
            )
            .split()
        )
        footer_pixmap = signed_document[-1].get_pixmap(
            clip=fitz.Rect(
                36,
                source_page_height,
                signed_document[-1].rect.width - 36,
                signed_document[-1].rect.height,
            ),
            alpha=False,
        )
        signed_document.close()
        local_signed_at = timezone.localtime(pv.signed_at)
        signature_statement = electronic_signature_statement(
            self.education,
            self.signataire,
            pv.signed_at,
        )
        self.assertGreater(signed_page_height, source_page_height)
        self.assertAlmostEqual(signed_text_position.x0, source_text_position.x0)
        self.assertAlmostEqual(signed_text_position.y0, source_text_position.y0)
        self.assertEqual(
            signature_statement,
            "تم توقيع هذا المحضر إلكترونياً من طرف سهيل بلاياشي، "
            "نيابةً عن الإدارة المستفيدة وزارة التربية الوطنية، "
            f"بتاريخ {local_signed_at:%d/%m/%Y}",
        )
        self.assertIn(f"{local_signed_at:%d/%m/%Y}", footer_text)
        footer_samples = footer_pixmap.samples
        dark_footer_pixels = sum(
            1
            for offset in range(0, len(footer_samples), footer_pixmap.n)
            if min(footer_samples[offset : offset + 3]) < 180
        )
        self.assertGreater(dark_footer_pixels, 300)
        self.assertNotIn("OTP", footer_text)
        self.assertNotIn("ATTESTATION", footer_text)
        self.assertNotIn("signataire", footer_text)
        self.assertNotIn("Responsable", footer_text)
        self.assertEqual(pdf_response.status_code, 403)

        self.client.force_login(self.admin_dde)
        dde_pdf_response = self.client.get(
            reverse("affectations:dde_signed_pv_pdf", args=[pv.id])
        )
        self.assertEqual(dde_pdf_response.status_code, 200)
        self.assertEqual(dde_pdf_response["Content-Type"], "application/pdf")
        b"".join(dde_pdf_response.streaming_content)

        signed_path = get_signed_pdf_path(pv)
        with open(signed_path, "ab") as signed_file:
            signed_file.write(b"\n% modification non autorisee")

        self.assertEqual(
            verify_signed_pv_integrity(pv).status,
            INTEGRITY_TAMPERED,
        )
        tampered_pdf_response = self.client.get(
            reverse("affectations:dde_signed_pv_pdf", args=[pv.id])
        )
        self.assertEqual(tampered_pdf_response.status_code, 403)

        admin_changelist_url = reverse(
            "admin:affectations_pvaffectation_changelist"
        )
        admin_response = self.client.get(admin_changelist_url)
        self.assertContains(admin_response, "Falsifié")
        self.assertContains(
            admin_response,
            "verify_selected_signed_pdf_integrity",
        )
        action_response = self.client.post(
            admin_changelist_url,
            {
                "action": "verify_selected_signed_pdf_integrity",
                "_selected_action": [str(pv.pk)],
            },
            follow=True,
        )
        self.assertContains(action_response, "falsifiés : 1")

        self.client.force_login(self.signataire)
        beneficiary_pdf_response = self.client.get(
            reverse("affectations:dde_signed_pv_pdf", args=[pv.id])
        )
        self.assertEqual(beneficiary_pdf_response.status_code, 403)
