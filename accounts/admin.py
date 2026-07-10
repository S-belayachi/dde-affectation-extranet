from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "administration",
        "role",
        "peut_signer",
        "is_active",
        "is_staff",
    )

    list_filter = (
        "role",
        "peut_signer",
        "is_active",
        "is_staff",
        "is_superuser",
        "administration",
    )

    search_fields = (
        "username",
        "first_name",
        "last_name",
        "email",
        "nom_ar",
        "prenom_ar",
        "cin",
        "matricule",
        "administration__nom",
        "administration__nom_ar",
    )

    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        ("Informations personnelles complémentaires", {
            "fields": (
                "nom_ar",
                "prenom_ar",
                "telephone",
                "cin",
                "matricule",
            )
        }),
        ("Affectation / Extranet", {
            "fields": (
                "administration",
                "role",
                "fonction",
                "peut_signer",
            )
        }),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Informations personnelles", {
            "fields": (
                "first_name",
                "last_name",
                "email",
                "nom_ar",
                "prenom_ar",
                "telephone",
                "cin",
                "matricule",
            )
        }),
        ("Affectation / Extranet", {
            "fields": (
                "administration",
                "role",
                "fonction",
                "peut_signer",
            )
        }),
    )