from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dwlr', '0003_live_data_provenance'),
    ]

    operations = [
        migrations.AlterField(
            model_name='waterqualityrecord',
            name='station_id',
            field=models.CharField(default='DWLR-001', max_length=80),
        ),
    ]
