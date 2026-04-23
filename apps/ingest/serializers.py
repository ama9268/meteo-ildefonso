from __future__ import annotations

import csv
import io
from typing import Any

from rest_framework import serializers

from .models import WeatherReading

PHYSICAL_LIMITS: dict[str, tuple[float, float]] = {
    "temperature_out": (-50.0, 60.0),
    "temperature_in": (-10.0, 60.0),
    "humidity_out": (0.0, 100.0),
    "humidity_in": (0.0, 100.0),
    "pressure": (870.0, 1084.0),
    "wind_speed": (0.0, 200.0),
    "wind_gust": (0.0, 250.0),
    "wind_dir": (0.0, 360.0),
    "uv_index": (0.0, 16.0),
    "solar_radiation": (0.0, 2000.0),
}


def _validate_physical(field: str, value: Any) -> Any:
    if value is None:
        return value
    lo, hi = PHYSICAL_LIMITS[field]
    if not (lo <= value <= hi):
        raise serializers.ValidationError(
            f"{field}: valor {value} fuera del rango físico [{lo}, {hi}]"
        )
    return value


class WeatherReadingSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherReading
        fields = "__all__"
        read_only_fields = ["id", "received_at", "raw_payload"]

    def validate_temperature_out(self, v: Any) -> Any:
        return _validate_physical("temperature_out", v)

    def validate_temperature_in(self, v: Any) -> Any:
        return _validate_physical("temperature_in", v)

    def validate_humidity_out(self, v: Any) -> Any:
        return _validate_physical("humidity_out", v)

    def validate_humidity_in(self, v: Any) -> Any:
        return _validate_physical("humidity_in", v)

    def validate_pressure(self, v: Any) -> Any:
        return _validate_physical("pressure", v)

    def validate_wind_speed(self, v: Any) -> Any:
        return _validate_physical("wind_speed", v)

    def validate_wind_gust(self, v: Any) -> Any:
        return _validate_physical("wind_gust", v)

    def validate_wind_dir(self, v: Any) -> Any:
        return _validate_physical("wind_dir", v)

    def validate_uv_index(self, v: Any) -> Any:
        return _validate_physical("uv_index", v)

    def validate_solar_radiation(self, v: Any) -> Any:
        return _validate_physical("solar_radiation", v)


def readings_to_csv(queryset) -> str:
    fields = [
        "id", "station_id", "received_at",
        "temperature_out", "temperature_in",
        "humidity_out", "humidity_in",
        "pressure", "wind_speed", "wind_gust", "wind_dir",
        "rain_rate", "rain_daily", "uv_index", "solar_radiation",
    ]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for r in queryset.values(*fields):
        writer.writerow(r)
    return output.getvalue()
