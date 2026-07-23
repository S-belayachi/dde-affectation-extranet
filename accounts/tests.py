from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from affectations.models import AdministrationBeneficiaire


User = get_user_model()


class AuthenticationFlowTests(TestCase):
    def setUp(self):
        self.education = AdministrationBeneficiaire.objects.create(
            nom="Education Nationale"
        )
        self.user = User.objects.create_user(
            username="beneficiary",
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

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/login/?next=/")

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "beneficiary",
                "password": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_user_can_switch_the_extranet_to_arabic(self):
        self.client.force_login(self.user)
        dashboard_url = reverse("accounts:dashboard")

        response = self.client.post(
            reverse("set_language"),
            {"language": "ar", "next": dashboard_url},
        )
        self.assertRedirects(response, dashboard_url)

        response = self.client.get(dashboard_url)

        self.assertContains(response, "لوحة التحكم")
        self.assertContains(response, 'lang="ar" dir="rtl"')

    def test_logout_redirects_to_login(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("accounts:logout"))

        self.assertRedirects(response, reverse("accounts:login"))

    def test_admin_dde_cannot_login_to_extranet(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": "admin_dde",
                "password": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ce compte est reserve")

    def test_admin_dde_cannot_access_extranet_dashboard(self):
        self.client.force_login(self.admin_dde)

        response = self.client.get(reverse("accounts:dashboard"))

        self.assertEqual(response.status_code, 403)

    def test_admin_dde_can_access_django_admin(self):
        self.client.force_login(self.admin_dde)

        response = self.client.get("/admin/")

        self.assertEqual(response.status_code, 200)


class OrganismUserManagementTests(TestCase):
    def setUp(self):
        self.education = AdministrationBeneficiaire.objects.create(
            nom="Education Nationale"
        )
        self.sports = AdministrationBeneficiaire.objects.create(
            nom="Jeunesse Et Sports"
        )
        self.org_admin = User.objects.create_user(
            username="org_admin",
            password="StrongPass123!",
            role=User.ROLE_ADMIN_ORGANISME,
            administration=self.education,
        )
        self.same_org_user = User.objects.create_user(
            username="same_org_user",
            password="StrongPass123!",
            role=User.ROLE_CONSULTATION,
            administration=self.education,
        )
        self.other_org_user = User.objects.create_user(
            username="other_org_user",
            password="StrongPass123!",
            role=User.ROLE_CONSULTATION,
            administration=self.sports,
        )
        self.consultation_user = User.objects.create_user(
            username="consultation_user",
            password="StrongPass123!",
            role=User.ROLE_CONSULTATION,
            administration=self.education,
        )

    def test_admin_organisme_lists_only_same_administration_users(self):
        self.client.force_login(self.org_admin)

        response = self.client.get(reverse("accounts:organism_user_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "same_org_user")
        self.assertNotContains(response, "other_org_user")
        self.assertNotIn(self.org_admin, response.context["managed_users"])

    def test_non_admin_organisme_cannot_access_user_management(self):
        self.client.force_login(self.consultation_user)

        response = self.client.get(reverse("accounts:organism_user_list"))

        self.assertEqual(response.status_code, 403)

    def test_admin_organisme_creates_user_inside_own_administration(self):
        self.client.force_login(self.org_admin)

        response = self.client.post(
            reverse("accounts:organism_user_create"),
            {
                "username": "created_signataire",
                "first_name": "Created",
                "last_name": "User",
                "email": "created@example.local",
                "nom_ar": "",
                "prenom_ar": "",
                "role": User.ROLE_SIGNATAIRE,
                "fonction": "Responsable",
                "telephone": "",
                "cin": "",
                "matricule": "",
                "peut_signer": "on",
                "is_active": "on",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        created_user = User.objects.get(username="created_signataire")
        self.assertRedirects(response, reverse("accounts:organism_user_list"))
        self.assertEqual(created_user.administration, self.education)
        self.assertEqual(created_user.role, User.ROLE_SIGNATAIRE)
        self.assertTrue(created_user.peut_signer)
        self.assertFalse(created_user.is_staff)
        self.assertFalse(created_user.is_superuser)

    def test_update_is_limited_to_same_administration(self):
        self.client.force_login(self.org_admin)

        response = self.client.post(
            reverse("accounts:organism_user_update", args=[self.same_org_user.id]),
            {
                "username": self.same_org_user.username,
                "first_name": "Edited",
                "last_name": "User",
                "email": "edited@example.local",
                "nom_ar": "",
                "prenom_ar": "",
                "role": User.ROLE_CONSULTATION,
                "fonction": "Edited",
                "telephone": "",
                "cin": "",
                "matricule": "",
                "peut_signer": "on",
                "is_active": "on",
            },
        )
        self.same_org_user.refresh_from_db()

        self.assertRedirects(response, reverse("accounts:organism_user_list"))
        self.assertEqual(self.same_org_user.first_name, "Edited")
        self.assertEqual(self.same_org_user.administration, self.education)
        self.assertEqual(self.same_org_user.role, User.ROLE_CONSULTATION)
        self.assertFalse(self.same_org_user.peut_signer)
        self.assertFalse(self.same_org_user.is_staff)
        self.assertFalse(self.same_org_user.is_superuser)

    def test_cross_administration_user_edit_returns_404(self):
        self.client.force_login(self.org_admin)

        response = self.client.get(
            reverse("accounts:organism_user_update", args=[self.other_org_user.id])
        )

        self.assertEqual(response.status_code, 404)
