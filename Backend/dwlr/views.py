from django.shortcuts import render

from rest_framework import viewsets
from .models import WaterQualityRecord
from .serializers import WaterQualityRecordSerializer

class WaterQualityRecordViewSet(viewsets.ModelViewSet):
    queryset = WaterQualityRecord.objects.all()
    serializer_class = WaterQualityRecordSerializer
