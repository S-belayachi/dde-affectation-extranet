from django.contrib import admin

from .models import (
    TableFaitAffectationDatalab,
    AdministrationBeneficiaire,
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
