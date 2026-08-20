from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import WaterQualityRecordViewSet

router = DefaultRouter()
router.register(r'water-quality', WaterQualityRecordViewSet, basename='waterqualityrecord')

urlpatterns = [
    path('', include(router.urls)),
]
