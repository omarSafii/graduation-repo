from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0006_projects_final_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='projects',
            name='rejection_reason',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='projects',
            name='resubmitted_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
