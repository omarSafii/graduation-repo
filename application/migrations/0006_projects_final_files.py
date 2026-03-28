from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0005_projects_workflow_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='projects',
            name='final_word_file',
            field=models.FileField(blank=True, null=True, upload_to='final_docs/'),
        ),
        migrations.AddField(
            model_name='projects',
            name='final_zip_file',
            field=models.FileField(blank=True, null=True, upload_to='final_code/'),
        ),
    ]
