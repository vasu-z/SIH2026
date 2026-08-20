from django.db import models

class WaterQualityRecord(models.Model):
    station_id = models.CharField(max_length=80, default="DWLR-001")
    lat = models.FloatField(default=28.6139)
    lon = models.FloatField(default=77.2090)
    date = models.DateField()
    water_level_m = models.FloatField(verbose_name="Water Level (m)")
    temperature_c = models.FloatField(null=True, blank=True, verbose_name="Temperature (°C)")
    rainfall_mm = models.FloatField(null=True, blank=True, verbose_name="Rainfall (mm)")
    ph = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True, verbose_name="pH")
    dissolved_oxygen_mg_l = models.FloatField(null=True, blank=True, verbose_name="Dissolved Oxygen (mg/L)")
    source = models.CharField(max_length=80, default="SYNTHETIC_SEED")
    source_agency = models.CharField(max_length=120, default="REPOSITORY_DEMO")
    source_url = models.URLField(blank=True, default="")
    source_record_id = models.CharField(max_length=120, blank=True, default="")
    observed_at = models.DateTimeField(null=True, blank=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    is_live_source = models.BooleanField(default=False)
    data_quality = models.CharField(max_length=40, default="DEMONSTRATION")

    def __str__(self):
        return f"{self.station_id} on {self.date}"
