from django.db import models

class WaterQualityRecord(models.Model):
    station_id = models.CharField(max_length=20, default="DWLR-001")
    lat = models.FloatField(default=28.6139)
    lon = models.FloatField(default=77.2090)
    date = models.DateField()
    water_level_m = models.FloatField(verbose_name="Water Level (m)")
    temperature_c = models.FloatField(verbose_name="Temperature (°C)")
    rainfall_mm = models.FloatField(verbose_name="Rainfall (mm)")
    ph = models.DecimalField(max_digits=4, decimal_places=2, verbose_name="pH")
    dissolved_oxygen_mg_l = models.FloatField(verbose_name="Dissolved Oxygen (mg/L)")

    def __str__(self):
        return f"{self.station_id} on {self.date}"