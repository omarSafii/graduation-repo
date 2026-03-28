from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0004_projectconversationmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='projects',
            name='edits_approved',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='projects',
            name='final_score_visible',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='projects',
            name='is_completed',
            field=models.BooleanField(default=False),
        ),
    ]
