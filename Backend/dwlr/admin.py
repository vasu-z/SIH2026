from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from .models import WaterQualityRecord
from import_export import resources, fields
from import_export.widgets import DateWidget
from django.contrib import admin

admin.site.site_header = "DLWR Backend Admin"
admin.site.site_title = "DLWR Admin Portal"
admin.site.index_title = "Welcome to the DLWR Admin Panel"

class WaterQualityRecordResource(resources.ModelResource):
    date = fields.Field(
        column_name='date',
        attribute='date',
        widget=DateWidget(format='%d-%m-%Y')  # Accepts DD-MM-YYYY
    )

    class Meta:
        model = WaterQualityRecord
        fields = (
            'id',
            'station_id',
            'lat',
            'lon',
            'date',
            'water_level_m',
            'temperature_c',
            'rainfall_mm',
            'ph',
            'dissolved_oxygen_mg_l',
            'source',
            'source_agency',
            'data_quality',
            'is_live_source',
        )
        import_id_fields = ['id']  # Optional: if you want updates by ID

@admin.register(WaterQualityRecord)
class WaterQualityRecordAdmin(ImportExportModelAdmin):
    resource_class = WaterQualityRecordResource
    list_display = ('station_id', 'date', 'water_level_m', 'source', 'data_quality', 'is_live_source')
    list_filter = ('date', 'source', 'data_quality', 'is_live_source')
    search_fields = ('station_id', 'source_agency', 'source_record_id')
