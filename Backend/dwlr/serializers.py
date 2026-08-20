from rest_framework import serializers
from .models import WaterQualityRecord

class WaterQualityRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterQualityRecord
        fields = '__all__'
