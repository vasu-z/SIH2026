from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WaterQualityRecordViewSet, stations_view, trust_view,
    incidents_view, forecast_view, optimize_view, scenario_run_view
)

router = DefaultRouter()
router.register(r'water-quality', WaterQualityRecordViewSet, basename='waterqualityrecord')

urlpatterns = [
    path('', include(router.urls)),
    path('stations/', stations_view),
    path('trust/<str:station_id>/', trust_view),
    path('incidents/', incidents_view),
    path('forecast/<str:station_id>/', forecast_view),
    path('optimize/', optimize_view),
    path('jalnetra/scenario/run/', scenario_run_view),
    path('scenario/run/', scenario_run_view),
]