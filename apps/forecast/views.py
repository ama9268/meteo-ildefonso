from __future__ import annotations

from django.utils.timezone import now
from django.views.generic import TemplateView

from .services import get_alerts, get_forecast


class ForecastView(TemplateView):
    template_name = "forecast/forecast.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["forecast"] = get_forecast()
        ctx["alerts"] = get_alerts()
        ctx["location"] = "Segura de León, Badajoz"
        # Coordenadas pasadas como strings con punto decimal para evitar
        # que la localización es-es de Django las renderice con coma en JS
        ctx["lat"] = "38.1203"
        ctx["lon"] = "-6.5308"
        ctx["last_updated"] = now()
        return ctx
