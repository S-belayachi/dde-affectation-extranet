from django.db import models
from django.conf import settings


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
    libelle_administration = models.TextField(blank=True, null=True)
    adresse_admi_en_arabe = models.TextField(blank=True, null=True)
    nom_administration = models.TextField(blank=True, null=True)
    adresse_admi_parent = models.TextField(blank=True, null=True)
    nom_admi_parent = models.TextField(blank=True, null=True)
    qualite_benefic = models.TextField(blank=True, null=True)
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


class Delegation(models.Model):
    code = models.CharField(max_length=50, unique=True)
    nom = models.CharField(max_length=200, unique=True)
    adresse = models.TextField()
    email = models.EmailField()

    class Meta:
        verbose_name = "Délégation"
        verbose_name_plural = "Délégations"
        ordering = ["nom"]

    def __str__(self):
        return f"{self.code} - {self.nom}"


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


class PvAffectation(models.Model):
    source_import_id = models.PositiveBigIntegerField()
    num_dossier = models.CharField(max_length=50, blank=True, null=True)
    numero_pv = models.CharField(max_length=50, blank=True, null=True)
    administration_source_nom = models.CharField(max_length=200)
    pv_key = models.CharField(max_length=255, unique=True)

    administration = models.ForeignKey(
        AdministrationBeneficiaire,
        on_delete=models.PROTECT,
        related_name="pv_affectations",
    )
    delegation = models.ForeignKey(
        Delegation,
        on_delete=models.PROTECT,
        related_name="pv_affectations",
        blank=True,
        null=True,
    )

    source_filename = models.CharField(max_length=500, blank=True)
    source_pdf_hash_sha256 = models.CharField(max_length=64, blank=True)
    dr_signed_pdf = models.CharField(max_length=500, blank=True)
    dr_pdf_hash_sha256 = models.CharField(max_length=64, blank=True)
    signed_pdf = models.CharField(max_length=500, blank=True)
    pdf_hash_sha256 = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    source_retrieved_at = models.DateTimeField(blank=True, null=True)
    is_signed_by_dr = models.BooleanField(default=False)
    signed_by_dr_at = models.DateTimeField(blank=True, null=True)
    is_signed = models.BooleanField(default=False)
    signed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "PV d'affectation"
        verbose_name_plural = "PV d'affectation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.num_dossier or '-'} / {self.numero_pv or '-'}"


class OtpCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="pv_otp_codes",
    )
    pv = models.ForeignKey(
        PvAffectation,
        on_delete=models.CASCADE,
        related_name="otp_codes",
    )
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    invalidated_at = models.DateTimeField(blank=True, null=True)
    invalidation_reason = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)

    class Meta:
        verbose_name = "Code OTP PV"
        verbose_name_plural = "Codes OTP PV"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP PV {self.pv_id} / {self.user_id}"


class DrOtpCode(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dr_pv_otp_codes",
    )
    pv = models.ForeignKey(
        PvAffectation,
        on_delete=models.CASCADE,
        related_name="dr_otp_codes",
    )
    code_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)
    invalidated_at = models.DateTimeField(blank=True, null=True)
    invalidation_reason = models.CharField(max_length=100, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)

    class Meta:
        verbose_name = "Code OTP PV DR"
        verbose_name_plural = "Codes OTP PV DR"
        ordering = ["-created_at"]

    def __str__(self):
        return f"OTP DR PV {self.pv_id} / {self.user_id}"


class SignatureOtpPv(models.Model):
    pv = models.OneToOneField(
        PvAffectation,
        on_delete=models.PROTECT,
        related_name="signature_proof",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="pv_signatures",
    )
    administration = models.ForeignKey(
        AdministrationBeneficiaire,
        on_delete=models.PROTECT,
        related_name="pv_signatures",
    )
    otp_verified = models.BooleanField(default=True)
    signed_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    pdf_hash_sha256 = models.CharField(max_length=64)
    pades_profile = models.CharField(max_length=30, blank=True)
    pades_signature_field = models.CharField(max_length=100, blank=True)
    pades_certificate_subject = models.TextField(blank=True)
    pades_certificate_serial_number = models.CharField(max_length=64, blank=True)
    pades_certificate_fingerprint_sha256 = models.CharField(
        max_length=64,
        blank=True,
    )

    class Meta:
        verbose_name = "Signature OTP PV"
        verbose_name_plural = "Signatures OTP PV"
        ordering = ["-signed_at"]

    def __str__(self):
        return f"Signature PV {self.pv_id} par {self.user_id}"


class SignatureOtpPvDr(models.Model):
    pv = models.OneToOneField(
        PvAffectation,
        on_delete=models.PROTECT,
        related_name="dr_signature_proof",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dr_pv_signatures",
    )
    delegation = models.ForeignKey(
        Delegation,
        on_delete=models.PROTECT,
        related_name="pv_signatures",
    )
    otp_verified = models.BooleanField(default=True)
    signed_at = models.DateTimeField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    pdf_hash_sha256 = models.CharField(max_length=64)
    pades_profile = models.CharField(max_length=30, blank=True)
    pades_signature_field = models.CharField(max_length=100, blank=True)
    pades_certificate_subject = models.TextField(blank=True)
    pades_certificate_serial_number = models.CharField(max_length=64, blank=True)
    pades_certificate_fingerprint_sha256 = models.CharField(
        max_length=64,
        blank=True,
    )

    class Meta:
        verbose_name = "Signature OTP PV DR"
        verbose_name_plural = "Signatures OTP PV DR"
        ordering = ["-signed_at"]

    def __str__(self):
        return f"Signature DR PV {self.pv_id} par {self.user_id}"
