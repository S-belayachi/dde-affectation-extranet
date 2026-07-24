from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models

from affectations.models import AdministrationBeneficiaire, Delegation


class CustomUser(AbstractUser):
    ROLE_CONSULTATION = "consultation"
    ROLE_SIGNATAIRE = "signataire"
    ROLE_ADMIN_ORGANISME = "admin_organisme"
    ROLE_ADMIN_DDE = "admin_dde"
    ROLE_SIGNATAIRE_DELEGATION = "signataire_delegation"

    ROLE_CHOICES = [
        (ROLE_CONSULTATION, "Consultation uniquement"),
        (ROLE_SIGNATAIRE, "Signataire"),
        (ROLE_ADMIN_ORGANISME, "Administrateur organisme"),
        (ROLE_ADMIN_DDE, "Administrateur DDE"),
        (ROLE_SIGNATAIRE_DELEGATION, "Signataire délégation"),
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

    delegation = models.ForeignKey(
        Delegation,
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
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(
                        role="signataire_delegation",
                        delegation__isnull=False,
                        administration__isnull=True,
                    )
                    | (
                        ~models.Q(role="signataire_delegation")
                        & models.Q(delegation__isnull=True)
                    )
                ),
                name="accounts_user_scope_matches_role",
            ),
        ]

    def __str__(self):
        full_name = self.get_full_name()
        return full_name if full_name else self.username

    def has_role(self, *roles):
        return self.role in roles

    def clean(self):
        super().clean()
        if self.is_delegation_signer:
            errors = {}
            if not self.delegation_id:
                errors["delegation"] = (
                    "Une délégation est obligatoire pour ce rôle."
                )
            if self.administration_id:
                errors["administration"] = (
                    "Un signataire de délégation ne peut pas être rattaché "
                    "à une administration bénéficiaire."
                )
            if errors:
                raise ValidationError(errors)
        elif self.delegation_id:
            raise ValidationError(
                {
                    "delegation": (
                        "Ce champ est réservé au rôle signataire délégation."
                    )
                }
            )

    @property
    def is_consultation_user(self):
        return self.has_role(self.ROLE_CONSULTATION)

    @property
    def is_signataire(self):
        return self.has_role(self.ROLE_SIGNATAIRE)

    @property
    def is_admin_organisme(self):
        return self.has_role(self.ROLE_ADMIN_ORGANISME)

    @property
    def is_admin_dde(self):
        return self.has_role(self.ROLE_ADMIN_DDE)

    @property
    def is_delegation_signer(self):
        return self.has_role(self.ROLE_SIGNATAIRE_DELEGATION)

    @property
    def can_consult_dossiers(self):
        return bool(
            self.administration_id
            and self.has_role(
                self.ROLE_CONSULTATION,
                self.ROLE_SIGNATAIRE,
                self.ROLE_ADMIN_ORGANISME,
            )
        )

    @property
    def can_sign_pv(self):
        return bool(
            self.administration_id
            and self.is_signataire
            and self.peut_signer
        )

    @property
    def can_sign_pv_dr(self):
        return bool(
            self.delegation_id
            and self.is_delegation_signer
            and self.peut_signer
        )

    @property
    def can_consult_dr_dossiers(self):
        return bool(self.delegation_id and self.is_delegation_signer)

    @property
    def otp_email(self):
        if self.is_delegation_signer and self.delegation_id:
            return (self.delegation.email or "").strip()
        return (self.email or "").strip()

    @property
    def can_manage_organism_users(self):
        return bool(self.administration_id and self.is_admin_organisme)

    @property
    def can_access_extranet(self):
        beneficiary_access = (
            self.administration_id
            and self.has_role(
                self.ROLE_CONSULTATION,
                self.ROLE_SIGNATAIRE,
                self.ROLE_ADMIN_ORGANISME,
            )
        )
        delegation_access = self.delegation_id and self.is_delegation_signer
        return bool(beneficiary_access or delegation_access)
