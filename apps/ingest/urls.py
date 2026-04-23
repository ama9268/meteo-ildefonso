from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import WeatherReadingViewSet, health, weather_ingest

router = DefaultRouter()
router.register(r"readings", WeatherReadingViewSet, basename="reading")

urlpatterns = [
    path("weather", weather_ingest, name="weather-ingest"),
    path("health/", health, name="health"),
    path("api/v1/", include(router.urls)),
]
