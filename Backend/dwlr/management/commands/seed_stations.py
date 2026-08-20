import numpy as np, datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from dwlr.models import WaterQualityRecord

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        WaterQualityRecord.objects.all().delete()
        rng = np.random.default_rng(42)
        stations = [(f"DWLR-{i:03d}", 20 + rng.uniform(0,10), 75 + rng.uniform(0,10)) for i in range(1, 21)]
        start = datetime.date.today() - datetime.timedelta(days=365)
        objs = []
        for sid, lat, lon in stations:
            base = rng.uniform(6, 12)
            trend = rng.choice([-0.003, 0, 0.002])
            for d in range(365):
                date = start + datetime.timedelta(days=d)
                level = base + trend*d + 0.5*np.sin(d/30) + rng.normal(0,0.15)
                objs.append(WaterQualityRecord(
                    station_id=sid, lat=lat, lon=lon, date=date,
                    water_level_m=round(level,2),
                    temperature_c=round(rng.uniform(18,32),1),
                    rainfall_mm=round(max(0, rng.normal(4,6)),1),
                    ph=Decimal(str(round(rng.uniform(6.5,8.2),2))),
                    dissolved_oxygen_mg_l=round(rng.uniform(4,9),2)
                ))
        WaterQualityRecord.objects.bulk_create(objs)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(objs)} records across {len(stations)} stations"))