from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    WaterQualityRecordViewSet, stations_view, trust_view,
    incidents_view, forecast_view, optimize_view, scenario_run_view,
    jalnetra_optimizer_run_view, jalnetra_trust_view, jalnetra_incidents_view,
    jalnetra_monitoring_priority_view, jalnetra_priority_view,
    jalnetra_unified_decision_view
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
    path('jalnetra/optimizer/run/', jalnetra_optimizer_run_view),
    path('optimizer/run/', jalnetra_optimizer_run_view),
    path('jalnetra/trust/<str:station_id>/', jalnetra_trust_view),
    path('jalnetra/incidents/', jalnetra_incidents_view),
    path('jalnetra/monitoring/priority/', jalnetra_monitoring_priority_view),
    path('monitoring/priority/', jalnetra_monitoring_priority_view),
    path('jalnetra/priority/', jalnetra_priority_view),
    path('priority/', jalnetra_priority_view),
    path('jalnetra/decision/unified/', jalnetra_unified_decision_view),
    path('decision/unified/', jalnetra_unified_decision_view),
]