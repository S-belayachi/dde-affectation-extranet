from django.contrib import admin

from django.urls import reverse
from django.utils.html import format_html

from .models import (
    TableFaitAffectationDatalab,
    AdministrationBeneficiaire,
    OtpCode,
    PvAffectation,
    SignatureOtpPv,
)


@admin.register(AdministrationBeneficiaire)
class AdministrationBeneficiaireAdmin(admin.ModelAdmin):
    list_display = (
        "nom",
        "nom_ar",
        "code",
        "email_contact",
        "telephone",
        "active",
    )

    search_fields = (
        "nom",
        "nom_ar",
        "code",
        "email_contact",
        "adresse_fr",
        "adresse_ar",
    )

    list_filter = ("active",)


@admin.register(TableFaitAffectationDatalab)
class TableFaitAffectationDatalabAdmin(admin.ModelAdmin):
    list_display = (
        "import_id",
        "num_dossier",
        "administration_beneficiaire",
        "type_affectation",
        "statut_dossier",
        "statut_pv",
    )

    search_fields = (
        "num_dossier",
        "administration_beneficiaire",
        "dr",
        "delegation",
        "num_id",
        "numero_pv",
    )

    list_filter = (
        "dr",
        "delegation",
        "type_affectation",
        "statut_dossier",
        "statut_pv",
        "mobilisable",
    )

    ordering = ("import_id",)

    readonly_fields = [
        field.name for field in TableFaitAffectationDatalab._meta.fields
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        view_permission = super().has_view_permission(request, obj)
        change_permission = admin.ModelAdmin.has_change_permission(self, request, obj)
        return view_permission or change_permission

    fieldsets = (
        ("Informations générales", {
            "fields": (
                "import_id",
                "dr",
                "delegation",
                "num_dossier",
                "type_affectation",
                "date_ouverture_dossier",
                "administration_beneficiaire",
                "denomination_projet",
                "statut_dossier",
            )
        }),

        ("Administration beneficiaire source", {
            "fields": (
                "libelle_administration",
                "adresse_admi_en_arabe",
                "nom_administration",
                "adresse_admi_parent",
                "nom_admi_parent",
                "qualite_benefic",
            )
        }),

        ("Bien concerné", {
            "fields": (
                "nature_sommier",
                "num_id",
                "trn",
                "num_trn",
                "indice_trn",
                "numero_construction",
                "nature_construction",
                "superficie_concernee",
                "superficie_proposee",
                "mobilisable",
            )
        }),

        ("Expertise et règlement", {
            "fields": (
                "date_resultat_enquete",
                "num_pv_expertise",
                "date_expertise",
                "montant_expertise",
                "montant_affectation",
                "date_pcv",
                "montant_total_regle",
                "num_fiche",
                "date_emission_fiche",
                "date_virement",
                "montant_fiche",
            )
        }),

        ("PV d’affectation", {
            "fields": (
                "numero_pv",
                "type_pv",
                "date_envoi_pva_dr",
                "statut_pv",
            )
        }),

        ("Constats", {
            "fields": (
                "constat_realisation",
                "date_constat_realisation",
                "constat_utilisation",
                "objet_utilisation",
                "date_constat_utilisation",
            )
        }),

        ("Désaffectation / clôture", {
            "fields": (
                "type_desaffectation",
                "motif_desaffectation",
                "date_cloture",
                "motif_cloture",
            )
        }),
    )


@admin.register(PvAffectation)
class PvAffectationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "num_dossier",
        "numero_pv",
        "administration",
        "is_signed",
        "generated_at",
        "signed_at",
        "signed_pdf_link",
    )
    search_fields = (
        "num_dossier",
        "numero_pv",
        "administration_source_nom",
        "pv_key",
    )
    list_filter = ("is_signed", "administration")
    readonly_fields = [field.name for field in PvAffectation._meta.fields]

    @admin.display(description="PDF signe")
    def signed_pdf_link(self, obj):
        if not obj.is_signed or not obj.generated_pdf:
            return "-"

        url = reverse("affectations:dde_signed_pv_pdf", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">Voir le PDF signe</a>', url)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        view_permission = super().has_view_permission(request, obj)
        change_permission = admin.ModelAdmin.has_change_permission(self, request, obj)
        return view_permission or change_permission


@admin.register(OtpCode)
class OtpCodeAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pv",
        "user",
        "created_at",
        "expires_at",
        "used_at",
        "attempts",
        "max_attempts",
    )
    search_fields = ("pv__num_dossier", "pv__numero_pv", "user__username")
    list_filter = ("used_at",)
    readonly_fields = [field.name for field in OtpCode._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        view_permission = super().has_view_permission(request, obj)
        change_permission = admin.ModelAdmin.has_change_permission(self, request, obj)
        return view_permission or change_permission


@admin.register(SignatureOtpPv)
class SignatureOtpPvAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pv",
        "user",
        "administration",
        "otp_verified",
        "signed_at",
    )
    search_fields = (
        "pv__num_dossier",
        "pv__numero_pv",
        "user__username",
        "administration__nom",
    )
    list_filter = ("otp_verified", "administration")
    readonly_fields = [field.name for field in SignatureOtpPv._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        view_permission = super().has_view_permission(request, obj)
        change_permission = admin.ModelAdmin.has_change_permission(self, request, obj)
        return view_permission or change_permission
