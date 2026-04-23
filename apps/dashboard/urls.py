from django.urls import path

from .views import DashboardView, HistoryView

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("history/", HistoryView.as_view(), name="history"),
]
