from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


User = get_user_model()


MANAGED_ORGANISM_ROLES = (
    User.ROLE_CONSULTATION,
    User.ROLE_SIGNATAIRE,
    User.ROLE_ADMIN_ORGANISME,
)


class ExtranetAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        "not_extranet_user": _(
            "Ce compte est reserve a l'administration interne DDE. "
            "Veuillez utiliser l'interface Django Admin."
        ),
    }

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)

        if not user.can_access_extranet:
            raise ValidationError(
                self.error_messages["not_extranet_user"],
                code="not_extranet_user",
            )


class OrganismUserBaseForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[
            (User.ROLE_CONSULTATION, _("Consultation uniquement")),
            (User.ROLE_SIGNATAIRE, _("Signataire")),
            (User.ROLE_ADMIN_ORGANISME, _("Administrateur organisme")),
        ],
        label=_("Role"),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "first_name",
            "last_name",
            "email",
            "nom_ar",
            "prenom_ar",
            "role",
            "fonction",
            "telephone",
            "cin",
            "matricule",
            "peut_signer",
            "is_active",
        )
        labels = {
            "username": _("Identifiant"),
            "first_name": _("Prenom"),
            "last_name": _("Nom"),
            "email": _("Email"),
            "nom_ar": _("Nom en arabe"),
            "prenom_ar": _("Prenom en arabe"),
            "fonction": _("Fonction"),
            "telephone": _("Telephone"),
            "matricule": _("Matricule"),
            "peut_signer": _("Peut signer"),
            "is_active": _("Compte actif"),
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("role") != User.ROLE_SIGNATAIRE:
            cleaned_data["peut_signer"] = False
        else:
            if not (cleaned_data.get("email") or "").strip():
                self.add_error(
                    "email",
                    _("Une adresse e-mail est obligatoire pour un signataire OTP."),
                )
            if not (cleaned_data.get("first_name") or "").strip():
                self.add_error(
                    "first_name",
                    _("Le prenom reel du signataire est obligatoire."),
                )
            if not (cleaned_data.get("last_name") or "").strip():
                self.add_error(
                    "last_name",
                    _("Le nom reel du signataire est obligatoire."),
                )
        return cleaned_data


class OrganismUserCreateForm(OrganismUserBaseForm):
    password1 = forms.CharField(
        label=_("Mot de passe"),
        strip=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label=_("Confirmation du mot de passe"),
        strip=False,
        widget=forms.PasswordInput,
    )

    class Meta(OrganismUserBaseForm.Meta):
        fields = OrganismUserBaseForm.Meta.fields + ("password1", "password2")

    def __init__(self, *args, administration, **kwargs):
        super().__init__(*args, **kwargs)
        self.administration = administration

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error("password2", _("Les deux mots de passe ne correspondent pas."))

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.administration = self.administration
        user.is_staff = False
        user.is_superuser = False
        user.set_password(self.cleaned_data["password1"])

        if commit:
            user.save()

        return user


class OrganismUserUpdateForm(OrganismUserBaseForm):
    def __init__(self, *args, administration, **kwargs):
        super().__init__(*args, **kwargs)
        self.administration = administration

    def save(self, commit=True):
        user = super().save(commit=False)
        user.administration = self.administration
        user.is_staff = False
        user.is_superuser = False

        if commit:
            user.save()

        return user
