from django.db import migrations, models


def sync_existing_supervisors(apps, schema_editor):
    Supervisor = apps.get_model('application', 'Supervisor')
    Supervisor.objects.filter(approval_status='').update(approval_status='approved')
    Supervisor.objects.filter(approval_status__isnull=True).update(approval_status='approved')
    Supervisor.objects.filter(university_id_card='').update(approval_status='approved')


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0008_supervisor_university_id_card_and_general_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='student',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='supervisor',
            name='approval_status',
            field=models.CharField(default='pending', max_length=20),
        ),
        migrations.AddField(
            model_name='supervisor',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(sync_existing_supervisors, migrations.RunPython.noop),
    ]
