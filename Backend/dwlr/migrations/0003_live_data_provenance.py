# Generated for JalNetra live data provenance.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dwlr', '0002_waterqualityrecord_lat_waterqualityrecord_lon_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='waterqualityrecord',
            name='temperature_c',
            field=models.FloatField(blank=True, null=True, verbose_name='Temperature (°C)'),
        ),
        migrations.AlterField(
            model_name='waterqualityrecord',
            name='rainfall_mm',
            field=models.FloatField(blank=True, null=True, verbose_name='Rainfall (mm)'),
        ),
        migrations.AlterField(
            model_name='waterqualityrecord',
            name='ph',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=4, null=True, verbose_name='pH'),
        ),
        migrations.AlterField(
            model_name='waterqualityrecord',
            name='dissolved_oxygen_mg_l',
            field=models.FloatField(blank=True, null=True, verbose_name='Dissolved Oxygen (mg/L)'),
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='source',
            field=models.CharField(default='SYNTHETIC_SEED', max_length=80),
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='source_agency',
            field=models.CharField(default='REPOSITORY_DEMO', max_length=120),
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='source_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='source_record_id',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='observed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='imported_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='is_live_source',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='waterqualityrecord',
            name='data_quality',
            field=models.CharField(default='DEMONSTRATION', max_length=40),
        ),
    ]
