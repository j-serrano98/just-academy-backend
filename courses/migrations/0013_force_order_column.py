from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0012_extracurricularactivity_order'), 
    ]

    operations = [
        migrations.AddField(
            model_name='sectionactivitycontrol',
            name='order',
            field=models.IntegerField(blank=True, default=0, null=True),
        ),
    ]