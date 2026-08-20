from django.db import models

class WaterQualityRecord(models.Model):
    date = models.DateField()
    water_level_m = models.FloatField(verbose_name="Water Level (m)")
    temperature_c = models.FloatField(verbose_name="Temperature (°C)")
    rainfall_mm = models.FloatField(verbose_name="Rainfall (mm)")
    ph = models.DecimalField(max_digits=4, decimal_places=2, verbose_name="pH")
    dissolved_oxygen_mg_l = models.FloatField(verbose_name="Dissolved Oxygen (mg/L)")

    def __str__(self):
        return f"Water Quality Record on {self.date}"
