from django import forms
from django.contrib.auth import get_user_model


User = get_user_model()


MANAGED_ORGANISM_ROLES = (
    User.ROLE_CONSULTATION,
    User.ROLE_SIGNATAIRE,
    User.ROLE_ADMIN_ORGANISME,
)


class OrganismUserBaseForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=[
            (User.ROLE_CONSULTATION, "Consultation uniquement"),
            (User.ROLE_SIGNATAIRE, "Signataire"),
            (User.ROLE_ADMIN_ORGANISME, "Administrateur organisme"),
        ],
        label="Role",
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
            "username": "Identifiant",
            "first_name": "Prenom",
            "last_name": "Nom",
            "email": "Email",
            "nom_ar": "Nom en arabe",
            "prenom_ar": "Prenom en arabe",
            "fonction": "Fonction",
            "telephone": "Telephone",
            "matricule": "Matricule",
            "peut_signer": "Peut signer",
            "is_active": "Compte actif",
        }

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("role") != User.ROLE_SIGNATAIRE:
            cleaned_data["peut_signer"] = False
        return cleaned_data


class OrganismUserCreateForm(OrganismUserBaseForm):
    password1 = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label="Confirmation du mot de passe",
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
            self.add_error("password2", "Les deux mots de passe ne correspondent pas.")

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
