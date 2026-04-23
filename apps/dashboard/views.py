from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView

from apps.ingest.models import WeatherReading


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["latest"] = WeatherReading.objects.order_by("-received_at").first()
        return ctx


class HistoryView(LoginRequiredMixin, ListView):
    model = WeatherReading
    template_name = "dashboard/history.html"
    context_object_name = "readings"
    paginate_by = 50
    ordering = ["-received_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        date_from = self.request.GET.get("from")
        date_to = self.request.GET.get("to")
        if date_from:
            qs = qs.filter(received_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(received_at__date__lte=date_to)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["date_from"] = self.request.GET.get("from", "")
        ctx["date_to"] = self.request.GET.get("to", "")
        return ctx
