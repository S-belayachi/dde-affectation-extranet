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
from pyhanko.pdf_utils.reader import PdfFileReader

from .models import (
    AdministrationBeneficiaire,
    Delegation,
    DrOtpCode,
    OtpCode,
    PvAffectation,
    SignatureOtpPv,
    SignatureOtpPvDr,
    TableFaitAffectationDatalab,
)
from .services.pv_documents import (
    INTEGRITY_TAMPERED,
    INTEGRITY_VALID,
    calculate_sha256,
    electronic_signature_statement,
    get_dr_signed_pdf_path,
    get_signed_pdf_path,
    retrieve_official_pv,
    verify_dr_signed_pv_integrity,
    verify_signed_pv_integrity,
)
from .services.pades_signature import PADES_PROFILE, validate_pades_signature
from .services.dr_rules import DR_READY_STATUSES
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
        self.agadir = Delegation.objects.create(
            code="DEL-AGADIR",
            nom="Agadir",
            adresse="Adresse Agadir",
            email="agadir@example.test",
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
        self.agadir_signer = User.objects.create_user(
            username="agadir_signer",
            password="StrongPass123!",
            role=User.ROLE_SIGNATAIRE_DELEGATION,
            delegation=self.agadir,
            peut_signer=True,
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
        TableFaitAffectationDatalab.objects.create(
            num_dossier="AGADIR-VALID",
            delegation="Agadir",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Projet Agadir valide",
            statut_pv=next(iter(DR_READY_STATUSES)),
        )
        TableFaitAffectationDatalab.objects.create(
            num_dossier="AGADIR-SIGNED",
            delegation="Agadir",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Projet Agadir deja signe",
            statut_pv="Signé",
        )
        TableFaitAffectationDatalab.objects.create(
            num_dossier="RABAT-VALID",
            delegation="Rabat",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Projet Rabat valide",
            statut_pv=next(iter(DR_READY_STATUSES)),
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

    def test_delegation_signer_sees_only_own_validated_dossiers(self):
        self.client.force_login(self.agadir_signer)

        response = self.client.get(
            reverse("affectations:delegation_dossier_list")
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AGADIR-VALID")
        self.assertContains(response, "Projet Agadir valide")
        self.assertNotContains(response, "AGADIR-SIGNED")
        self.assertNotContains(response, "RABAT-VALID")
        self.assertContains(
            response,
            reverse(
                "affectations:delegation_dossier_detail",
                args=[
                    TableFaitAffectationDatalab.objects.get(
                        num_dossier="AGADIR-VALID"
                    ).import_id
                ],
            ),
        )

    def test_beneficiary_and_dde_users_cannot_access_delegation_dossiers(self):
        delegation_url = reverse("affectations:delegation_dossier_list")

        self.client.force_login(self.education_user)
        self.assertEqual(self.client.get(delegation_url).status_code, 403)

        self.client.force_login(self.admin_dde)
        self.assertEqual(self.client.get(delegation_url).status_code, 403)

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
        self.assertEqual(signature_proof.pades_profile, PADES_PROFILE)
        self.assertEqual(
            signature_proof.pades_signature_field,
            f"BeneficiarySignature_{pv.pk}",
        )
        self.assertIn(
            "CN=Souhayl Belayachi",
            signature_proof.pades_certificate_subject,
        )
        self.assertIn(
            "O=Education Nationale",
            signature_proof.pades_certificate_subject,
        )
        self.assertTrue(signature_proof.pades_certificate_serial_number)
        self.assertEqual(
            len(signature_proof.pades_certificate_fingerprint_sha256),
            64,
        )
        self.assertEqual(verify_signed_pv_integrity(pv).status, INTEGRITY_VALID)
        signed_path = get_signed_pdf_path(pv)
        pades_result = validate_pades_signature(
            signed_path,
            expected_field_name=signature_proof.pades_signature_field,
            expected_fingerprint_sha256=(
                signature_proof.pades_certificate_fingerprint_sha256
            ),
        )
        self.assertTrue(pades_result.is_valid)
        with open(signed_path, "rb") as signed_file:
            signed_reader = PdfFileReader(signed_file)
            embedded_signature = next(
                signature
                for signature in signed_reader.embedded_signatures
                if signature.field_name == signature_proof.pades_signature_field
            )
            self.assertEqual(
                str(embedded_signature.sig_object.get("/SubFilter")),
                "/ETSI.CAdES.detached",
            )
            self.assertEqual(
                list(embedded_signature.sig_field.get("/Rect")),
                [0, 0, 0, 0],
            )

        signed_document = fitz.open(signed_path)
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
            f"بتاريخ {local_signed_at:%d/%m/%Y} "
            f"على الساعة {local_signed_at:%H:%M:%S}",
        )
        self.assertIn(f"{local_signed_at:%d/%m/%Y}", footer_text)
        self.assertIn(f"{local_signed_at:%H:%M:%S}", footer_text)
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

        tampered_document = fitz.open(signed_path)
        tampered_document[0].insert_text(
            fitz.Point(72, 120),
            "Modification non autorisee",
        )
        tampered_document.saveIncr()
        tampered_document.close()

        self.assertFalse(
            validate_pades_signature(
                signed_path,
                expected_field_name=signature_proof.pades_signature_field,
                expected_fingerprint_sha256=(
                    signature_proof.pades_certificate_fingerprint_sha256
                ),
            ).is_valid
        )
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


class DrPvSignatureFlowTests(TestCase):
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
            DR_SIGNED_PV_ROOT=self.document_root / "dr_signed",
            SIGNED_PV_ROOT=self.document_root / "signed",
        )
        self.override.enable()
        self.addCleanup(self.override.disable)

        self.education = AdministrationBeneficiaire.objects.create(
            nom="Education Nationale"
        )
        self.agadir = Delegation.objects.create(
            code="DEL-AGADIR",
            nom="Agadir",
            adresse="Adresse Agadir",
            email="agadir@example.test",
        )
        self.rabat = Delegation.objects.create(
            code="DEL-RABAT",
            nom="Rabat",
            adresse="Adresse Rabat",
            email="rabat@example.test",
        )
        self.dr_signer = User.objects.create_user(
            username="delegation_agadir",
            password="StrongPass123!",
            first_name="Souhayl",
            last_name="Belayachi",
            role=User.ROLE_SIGNATAIRE_DELEGATION,
            delegation=self.agadir,
            peut_signer=True,
        )
        self.other_dr_signer = User.objects.create_user(
            username="delegation_rabat",
            password="StrongPass123!",
            first_name="Autre",
            last_name="Signataire",
            role=User.ROLE_SIGNATAIRE_DELEGATION,
            delegation=self.rabat,
            peut_signer=True,
        )
        self.beneficiary_signer = User.objects.create_user(
            username="education_signer",
            password="StrongPass123!",
            first_name="Beneficiaire",
            last_name="Signataire",
            email="beneficiary@example.test",
            role=User.ROLE_SIGNATAIRE,
            administration=self.education,
            peut_signer=True,
        )
        self.dossier = TableFaitAffectationDatalab.objects.create(
            num_dossier="AGADIR-DR-001",
            delegation="Agadir",
            administration_beneficiaire="Education Nationale",
            denomination_projet="Projet a signer par la DR",
            numero_pv="PV-DR-001",
            statut_pv=next(iter(DR_READY_STATUSES)),
        )
        self.create_official_pdf()

    def create_official_pdf(self):
        path = (
            self.document_root
            / "official"
            / f"{self.dossier.import_id}.pdf"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        document = fitz.open()
        page = document.new_page()
        page.insert_text((72, 72), "PV officiel en attente de signature DR")
        document.save(path)
        document.close()

    def prepare_pv(self):
        pv, _source_path = retrieve_official_pv(
            self.dossier,
            self.education,
        )
        pv.delegation = self.agadir
        pv.save(update_fields=["delegation"])
        return pv

    def test_delegation_detail_exposes_pv_and_otp_actions(self):
        self.client.force_login(self.dr_signer)

        response = self.client.get(
            reverse(
                "affectations:delegation_dossier_detail",
                args=[self.dossier.import_id],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Consulter le PV")
        self.assertContains(response, "Demander OTP")
        self.assertContains(response, "Signer par OTP")

    def test_missing_official_pv_is_reported_without_debug_404(self):
        official_path = (
            self.document_root
            / "official"
            / f"{self.dossier.import_id}.pdf"
        )
        official_path.unlink()
        self.client.force_login(self.dr_signer)

        detail_response = self.client.get(
            reverse(
                "affectations:delegation_dossier_detail",
                args=[self.dossier.import_id],
            )
        )
        pdf_response = self.client.get(
            reverse(
                "affectations:delegation_pv_pdf",
                args=[self.dossier.import_id],
            )
        )

        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "PV officiel indisponible")
        self.assertContains(
            detail_response,
            f"Fichier attendu : {self.dossier.import_id}.pdf",
        )
        self.assertNotContains(detail_response, "Consulter le PV")
        self.assertNotContains(detail_response, "Demander OTP")
        self.assertEqual(pdf_response.status_code, 302)
        self.assertEqual(
            pdf_response["Location"],
            reverse(
                "affectations:delegation_dossier_detail",
                args=[self.dossier.import_id],
            ),
        )

    def test_other_delegation_cannot_access_dr_signature_views(self):
        self.client.force_login(self.other_dr_signer)

        detail_response = self.client.get(
            reverse(
                "affectations:delegation_dossier_detail",
                args=[self.dossier.import_id],
            )
        )
        pdf_response = self.client.get(
            reverse(
                "affectations:delegation_pv_pdf",
                args=[self.dossier.import_id],
            )
        )

        self.assertEqual(detail_response.status_code, 403)
        self.assertEqual(pdf_response.status_code, 403)

    def test_dr_otp_is_hashed_and_sent_to_delegation_email(self):
        self.client.force_login(self.dr_signer)

        response = self.client.post(
            reverse(
                "affectations:delegation_pv_otp_request",
                args=[self.dossier.import_id],
            )
        )

        self.assertEqual(response.status_code, 302)
        otp = DrOtpCode.objects.get()
        self.assertNotRegex(otp.code_hash, r"^\d{6}$")
        self.assertEqual(mail.outbox[0].to, [self.agadir.email])

    def test_successful_dr_signature_hands_dossier_to_beneficiary(self):
        pv = self.prepare_pv()
        DrOtpCode.objects.create(
            user=self.dr_signer,
            pv=pv,
            code_hash=make_password("123456"),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        self.client.force_login(self.dr_signer)

        response = self.client.post(
            reverse(
                "affectations:delegation_pv_otp_verify",
                args=[self.dossier.import_id],
            ),
            {"otp_code": "123456"},
            HTTP_USER_AGENT="DR test agent",
        )

        self.assertEqual(response.status_code, 302)
        pv.refresh_from_db()
        self.dossier.refresh_from_db()
        self.assertTrue(pv.is_signed_by_dr)
        self.assertFalse(pv.is_signed)
        self.assertIsNotNone(pv.signed_by_dr_at)
        self.assertTrue(pv.dr_signed_pdf.startswith("dr_signed"))
        self.assertEqual(self.dossier.statut_pv, next(iter(DR_READY_STATUSES)))

        proof = SignatureOtpPvDr.objects.get(pv=pv)
        self.assertTrue(proof.otp_verified)
        self.assertEqual(proof.user, self.dr_signer)
        self.assertEqual(proof.delegation, self.agadir)
        self.assertEqual(proof.user_agent, "DR test agent")
        self.assertEqual(proof.pdf_hash_sha256, pv.dr_pdf_hash_sha256)
        self.assertEqual(proof.pades_profile, PADES_PROFILE)
        self.assertEqual(proof.pades_signature_field, f"DrSignature_{pv.pk}")
        self.assertEqual(
            verify_dr_signed_pv_integrity(pv).status,
            INTEGRITY_VALID,
        )
        self.assertTrue(get_dr_signed_pdf_path(pv).is_file())

        delegation_pdf_response = self.client.get(
            reverse(
                "affectations:delegation_pv_pdf",
                args=[self.dossier.import_id],
            )
        )
        delegation_list_response = self.client.get(
            reverse("affectations:delegation_dossier_list")
        )
        self.assertEqual(delegation_pdf_response.status_code, 403)
        self.assertNotContains(delegation_list_response, self.dossier.num_dossier)

        self.client.force_login(self.beneficiary_signer)
        beneficiary_list_response = self.client.get(
            reverse("affectations:dossier_list")
        )
        beneficiary_detail_response = self.client.get(
            reverse(
                "affectations:dossier_detail",
                args=[self.dossier.import_id],
            )
        )
        beneficiary_pdf_response = self.client.get(
            reverse(
                "affectations:pv_pdf",
                args=[self.dossier.import_id],
            )
        )
        self.assertContains(beneficiary_list_response, self.dossier.num_dossier)
        self.assertContains(beneficiary_detail_response, "Signer par OTP")
        self.assertEqual(beneficiary_pdf_response.status_code, 200)
        self.assertEqual(
            beneficiary_pdf_response["Content-Type"],
            "application/pdf",
        )
        b"".join(beneficiary_pdf_response.streaming_content)

        OtpCode.objects.create(
            user=self.beneficiary_signer,
            pv=pv,
            code_hash=make_password("654321"),
            expires_at=timezone.now() + timezone.timedelta(minutes=10),
        )
        beneficiary_sign_response = self.client.post(
            reverse(
                "affectations:pv_otp_verify",
                args=[self.dossier.import_id],
            ),
            {"otp_code": "654321"},
            HTTP_USER_AGENT="Beneficiary test agent",
        )

        self.assertEqual(beneficiary_sign_response.status_code, 302)
        pv.refresh_from_db()
        self.assertTrue(pv.is_signed_by_dr)
        self.assertTrue(pv.is_signed)
        self.assertEqual(verify_dr_signed_pv_integrity(pv).status, INTEGRITY_VALID)
        self.assertEqual(verify_signed_pv_integrity(pv).status, INTEGRITY_VALID)

        final_path = get_signed_pdf_path(pv)
        beneficiary_proof = SignatureOtpPv.objects.get(pv=pv)
        with open(final_path, "rb") as final_file:
            final_reader = PdfFileReader(final_file)
            signature_fields = {
                signature.field_name
                for signature in final_reader.embedded_signatures
            }
        self.assertEqual(
            signature_fields,
            {
                proof.pades_signature_field,
                beneficiary_proof.pades_signature_field,
            },
        )
        self.assertTrue(
            validate_pades_signature(
                final_path,
                expected_field_name=proof.pades_signature_field,
                expected_fingerprint_sha256=(
                    proof.pades_certificate_fingerprint_sha256
                ),
                allow_later_signatures=True,
            ).is_valid
        )
        self.assertTrue(
            validate_pades_signature(
                final_path,
                expected_field_name=beneficiary_proof.pades_signature_field,
                expected_fingerprint_sha256=(
                    beneficiary_proof.pades_certificate_fingerprint_sha256
                ),
            ).is_valid
        )
