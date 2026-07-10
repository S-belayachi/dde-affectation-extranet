from django.db import models


# Imported DDE/AMLACS source data. This table is owned outside Django and must
# stay unmanaged: do not remove `managed = False` or let migrations alter it.

class TableFaitAffectationDatalab(models.Model):
    import_id = models.BigAutoField(primary_key=True)
    dr = models.CharField(max_length=150, blank=True, null=True)
    delegation = models.CharField(max_length=100, blank=True, null=True)
    num_dossier = models.CharField(max_length=50, blank=True, null=True)
    type_affectation = models.CharField(max_length=100, blank=True, null=True)
    date_ouverture_dossier = models.DateField(blank=True, null=True)
    denomination_projet = models.TextField(blank=True, null=True)
    administration_beneficiaire = models.CharField(max_length=200, blank=True, null=True)
    nature_sommier = models.CharField(max_length=100, blank=True, null=True)
    num_id = models.CharField(max_length=50, blank=True, null=True)
    trn = models.CharField(max_length=20, blank=True, null=True)
    num_trn = models.CharField(max_length=50, blank=True, null=True)
    indice_trn = models.CharField(max_length=50, blank=True, null=True)
    numero_construction = models.CharField(max_length=50, blank=True, null=True)
    nature_construction = models.TextField(blank=True, null=True)
    superficie_concernee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    montant_affectation = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    statut_dossier = models.CharField(max_length=100, blank=True, null=True)
    date_resultat_enquete = models.DateField(blank=True, null=True)
    mobilisable = models.TextField(blank=True, null=True)  # This field type is a guess.
    superficie_proposee = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    num_pv_expertise = models.CharField(max_length=50, blank=True, null=True)
    date_expertise = models.DateField(blank=True, null=True)
    montant_expertise = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    date_pcv = models.DateField(blank=True, null=True)
    montant_total_regle = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    num_fiche = models.CharField(max_length=50, blank=True, null=True)
    date_emission_fiche = models.DateField(blank=True, null=True)
    date_virement = models.DateField(blank=True, null=True)
    montant_fiche = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    numero_pv = models.CharField(max_length=50, blank=True, null=True)
    type_pv = models.CharField(max_length=100, blank=True, null=True)
    date_envoi_pva_dr = models.DateField(blank=True, null=True)
    statut_pv = models.CharField(max_length=100, blank=True, null=True)
    constat_realisation = models.TextField(blank=True, null=True)
    date_constat_realisation = models.DateField(blank=True, null=True)
    constat_utilisation = models.TextField(blank=True, null=True)
    objet_utilisation = models.TextField(blank=True, null=True)
    date_constat_utilisation = models.DateField(blank=True, null=True)
    type_desaffectation = models.CharField(max_length=100, blank=True, null=True)
    motif_desaffectation = models.TextField(blank=True, null=True)
    date_cloture = models.DateField(blank=True, null=True)
    motif_cloture = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'table_fait_affectation_datalab'


class AdministrationBeneficiaire(models.Model):
    nom = models.CharField(max_length=200, unique=True)
    nom_ar = models.CharField("Nom en arabe", max_length=200, blank=True, null=True)

    code = models.CharField(max_length=50, blank=True, null=True)

    adresse_fr = models.TextField("Adresse en français", blank=True, null=True)
    adresse_ar = models.TextField("Adresse en arabe", blank=True, null=True)

    email_contact = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=30, blank=True, null=True)
    active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Administration bénéficiaire"
        verbose_name_plural = "Administrations bénéficiaires"
        ordering = ["nom"]

    def __str__(self):
        return self.nom
