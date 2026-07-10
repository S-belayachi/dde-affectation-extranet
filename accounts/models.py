from django.contrib.auth.models import AbstractUser
from django.db import models

from affectations.models import AdministrationBeneficiaire


class CustomUser(AbstractUser):
    ROLE_CONSULTATION = "consultation"
    ROLE_SIGNATAIRE = "signataire"
    ROLE_ADMIN_ORGANISME = "admin_organisme"
    ROLE_ADMIN_DDE = "admin_dde"

    ROLE_CHOICES = [
        (ROLE_CONSULTATION, "Consultation uniquement"),
        (ROLE_SIGNATAIRE, "Signataire"),
        (ROLE_ADMIN_ORGANISME, "Administrateur organisme"),
        (ROLE_ADMIN_DDE, "Administrateur DDE"),
    ]

    nom_ar = models.CharField("Nom en arabe", max_length=150, blank=True, null=True)
    prenom_ar = models.CharField("Prénom en arabe", max_length=150, blank=True, null=True)

    administration = models.ForeignKey(
        AdministrationBeneficiaire,
        on_delete=models.PROTECT,
        related_name="utilisateurs",
        blank=True,
        null=True,
    )

    role = models.CharField(
        max_length=30,
        choices=ROLE_CHOICES,
        default=ROLE_CONSULTATION,
    )

    fonction = models.CharField(max_length=150, blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    cin = models.CharField("CIN", max_length=20, blank=True, null=True)
    matricule = models.CharField(max_length=50, blank=True, null=True)

    peut_signer = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"

    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username