from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("affectations", "0004_source_administration_fields_state"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="pvaffectation",
            name="template_name",
        ),
        migrations.RemoveField(
            model_name="pvaffectation",
            name="generated_docx",
        ),
        migrations.RenameField(
            model_name="pvaffectation",
            old_name="generated_pdf",
            new_name="signed_pdf",
        ),
        migrations.RenameField(
            model_name="pvaffectation",
            old_name="generated_at",
            new_name="source_retrieved_at",
        ),
        migrations.AddField(
            model_name="pvaffectation",
            name="source_filename",
            field=models.CharField(blank=True, max_length=500),
        ),
        migrations.AddField(
            model_name="pvaffectation",
            name="source_pdf_hash_sha256",
            field=models.CharField(blank=True, max_length=64),
        ),
    ]
