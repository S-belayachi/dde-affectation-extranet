from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from .models import AdministrationBeneficiaire, TableFaitAffectationDatalab


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
