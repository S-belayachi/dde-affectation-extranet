# This migration records external source-table columns in Django's model state.
# The physical columns are added directly to the source database, which remains
# unmanaged by Django.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("affectations", "0003_otpcode_invalidated_at_otpcode_invalidation_reason"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name="tablefaitaffectationdatalab",
                    name="libelle_administration",
                    field=models.TextField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="tablefaitaffectationdatalab",
                    name="adresse_admi_en_arabe",
                    field=models.TextField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="tablefaitaffectationdatalab",
                    name="nom_administration",
                    field=models.TextField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="tablefaitaffectationdatalab",
                    name="adresse_admi_parent",
                    field=models.TextField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="tablefaitaffectationdatalab",
                    name="nom_admi_parent",
                    field=models.TextField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="tablefaitaffectationdatalab",
                    name="qualite_benefic",
                    field=models.TextField(blank=True, null=True),
                ),
            ],
            database_operations=[],
        ),
    ]
