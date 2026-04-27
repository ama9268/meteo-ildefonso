from django.urls import path

from .views import ForecastView

urlpatterns = [
    path("prevision/", ForecastView.as_view(), name="forecast"),
]
