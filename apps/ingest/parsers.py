"""
Conversión de unidades del protocolo Bresser/WU (imperial) a SI.
Todas las funciones reciben el valor como str o float y devuelven float o None.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _to_float(value: Any, field: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        logger.warning("parsers: no se pudo convertir '%s' en campo '%s'", value, field)
        return None


def f_to_c(value: Any) -> float | None:
    v = _to_float(value, "temperature_f")
    return round((v - 32) * 5 / 9, 2) if v is not None else None


def mph_to_kmh(value: Any) -> float | None:
    v = _to_float(value, "wind_mph")
    return round(v * 1.60934, 2) if v is not None else None


def inhg_to_hpa(value: Any) -> float | None:
    v = _to_float(value, "pressure_inhg")
    return round(v * 33.8639, 2) if v is not None else None


def in_to_mm(value: Any) -> float | None:
    v = _to_float(value, "rain_in")
    return round(v * 25.4, 2) if v is not None else None


def parse_bresser_payload(payload: dict) -> dict:
    """
    Traduce los query params de la estación Bresser al dict de campos del modelo.
    Los campos que no se reconocen se ignoran (se conservan en raw_payload).
    """
    return {
        "temperature_out": f_to_c(payload.get("tempf")),
        "temperature_in": f_to_c(payload.get("indoortempf")),
        "humidity_out": _to_float(payload.get("humidity"), "humidity_out"),
        "humidity_in": _to_float(payload.get("indoorhumidity"), "humidity_in"),
        "pressure": inhg_to_hpa(payload.get("baromin")),
        "wind_speed": mph_to_kmh(payload.get("windspeedmph")),
        "wind_gust": mph_to_kmh(payload.get("windgustmph")),
        "wind_dir": _to_float(payload.get("winddir"), "wind_dir"),
        "rain_rate": in_to_mm(payload.get("rainin")),
        "rain_daily": in_to_mm(payload.get("dailyrainin")),
        "uv_index": _to_float(payload.get("UV") or payload.get("uv"), "uv_index"),
        "solar_radiation": _to_float(payload.get("solarradiation"), "solar_radiation"),
    }
