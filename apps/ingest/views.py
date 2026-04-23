from __future__ import annotations

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from apps.alerts.services import check_alerts

from .models import WeatherReading
from .parsers import parse_bresser_payload
from .serializers import WeatherReadingSerializer, readings_to_csv

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def weather_ingest(request: HttpRequest) -> HttpResponse:
    payload = (
        request.GET.dict() if request.method == "GET" else request.POST.dict()
    )

    sid = payload.get("ID") or payload.get("station_id") or payload.get("stationid")
    skey = payload.get("PASSWORD") or payload.get("station_key") or payload.get("key")

    if sid != settings.STATION_ID or skey != settings.STATION_KEY:
        logger.warning("ingest: autenticación fallida sid=%s", sid)
        return HttpResponse("unauthorized", status=401)

    parsed = parse_bresser_payload(payload)
    reading = WeatherReading(
        station_id=sid,
        raw_payload=payload,
        **{k: v for k, v in parsed.items() if v is not None},
    )
    reading.save()

    logger.info(
        "ingest: lectura guardada id=%d station=%s at=%s",
        reading.pk,
        reading.station_id,
        reading.received_at.isoformat(),
    )

    check_alerts(reading)

    return HttpResponse("OK", content_type="text/plain", status=200)


def health(request: HttpRequest) -> HttpResponse:
    return HttpResponse('{"ok": true}', content_type="application/json")


class WeatherReadingViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WeatherReading.objects.all()
    serializer_class = WeatherReadingSerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ["received_at"]
    ordering = ["-received_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        from_dt = self.request.query_params.get("from")
        to_dt = self.request.query_params.get("to")
        station = self.request.query_params.get("station")
        if from_dt:
            qs = qs.filter(received_at__gte=from_dt)
        if to_dt:
            qs = qs.filter(received_at__lte=to_dt)
        if station:
            qs = qs.filter(station_id=station)
        return qs

    @action(detail=False, methods=["get"])
    def latest(self, request: Request) -> Response:
        reading = WeatherReading.objects.order_by("-received_at").first()
        if reading is None:
            return Response({"detail": "Sin datos"}, status=status.HTTP_404_NOT_FOUND)
        return Response(WeatherReadingSerializer(reading).data)

    @action(detail=False, methods=["get"])
    def export(self, request: Request) -> HttpResponse:
        qs = self.get_queryset()
        csv_data = readings_to_csv(qs)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        response = HttpResponse(csv_data, content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="readings_{ts}.csv"'
        return response

    @action(detail=False, methods=["get"])
    def chart(self, request: Request) -> Response:
        hours = int(request.query_params.get("hours", 24))
        from django.utils import timezone as dj_tz
        from datetime import timedelta
        since = dj_tz.now() - timedelta(hours=hours)
        qs = WeatherReading.objects.filter(received_at__gte=since).order_by("received_at")
        data = list(
            qs.values(
                "received_at", "temperature_out", "humidity_out",
                "pressure", "wind_speed", "rain_daily",
            )
        )
        for row in data:
            row["received_at"] = row["received_at"].isoformat()
        return Response(data)
