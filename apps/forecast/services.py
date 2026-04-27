from __future__ import annotations

import logging
from datetime import date

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

MUNICIPIO = "06124"  # Segura de León, Badajoz
AEMET_BASE = "https://opendata.aemet.es/opendata/api"
CACHE_TTL = 3 * 3600  # 3 horas

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = [
    "", "ene", "feb", "mar", "abr", "may", "jun",
    "jul", "ago", "sep", "oct", "nov", "dic",
]

# Código cielo → (emoji, descripción, clase Tailwind color)
SKY_STATES: dict[str, tuple[str, str, str]] = {
    "11":  ("☀️",  "Despejado",                        "text-yellow-500"),
    "11n": ("🌙",  "Despejado (noche)",                 "text-indigo-300"),
    "12":  ("🌤️", "Poco nuboso",                       "text-yellow-400"),
    "12n": ("🌤️", "Poco nuboso (noche)",               "text-indigo-400"),
    "13":  ("⛅",  "Intervalos nubosos",                "text-slate-400"),
    "13n": ("⛅",  "Intervalos nubosos (noche)",        "text-slate-500"),
    "14":  ("☁️",  "Nuboso",                            "text-slate-500"),
    "14n": ("☁️",  "Nuboso (noche)",                    "text-slate-600"),
    "15":  ("☁️",  "Muy nuboso",                        "text-slate-600"),
    "16":  ("☁️",  "Cubierto",                          "text-slate-700"),
    "17":  ("🌥️", "Nubes altas",                       "text-slate-300"),
    "23":  ("🌦️", "Intervalos nubosos con lluvia escasa","text-blue-400"),
    "24":  ("🌧️", "Nuboso con lluvia escasa",          "text-blue-500"),
    "25":  ("🌧️", "Muy nuboso con lluvia escasa",      "text-blue-600"),
    "26":  ("🌧️", "Cubierto con lluvia escasa",        "text-blue-700"),
    "33":  ("🌧️", "Intervalos nubosos con lluvia",     "text-blue-500"),
    "34":  ("🌧️", "Nuboso con lluvia",                 "text-blue-600"),
    "35":  ("🌧️", "Muy nuboso con lluvia",             "text-blue-700"),
    "36":  ("🌧️", "Cubierto con lluvia",               "text-blue-800"),
    "43":  ("🌨️", "Intervalos nubosos con lluvia y nieve","text-cyan-500"),
    "44":  ("🌨️", "Nuboso con lluvia y nieve",         "text-cyan-500"),
    "45":  ("❄️",  "Muy nuboso con nieve",              "text-cyan-400"),
    "46":  ("❄️",  "Cubierto con nieve",                "text-cyan-500"),
    "51":  ("⛈️",  "Intervalos nubosos con tormenta",  "text-purple-500"),
    "52":  ("⛈️",  "Nuboso con tormenta",              "text-purple-600"),
    "53":  ("⛈️",  "Muy nuboso con tormenta",          "text-purple-700"),
    "54":  ("⛈️",  "Cubierto con tormenta",            "text-purple-800"),
    "61":  ("🌩️", "Intervalos nubosos con tormenta y lluvia","text-purple-500"),
    "62":  ("🌩️", "Nuboso con tormenta y lluvia",      "text-purple-600"),
    "63":  ("🌩️", "Muy nuboso con tormenta y lluvia",  "text-purple-700"),
    "64":  ("🌩️", "Cubierto con tormenta y lluvia",    "text-purple-800"),
    "71":  ("🌨️", "Nieve escasa",                      "text-cyan-300"),
    "72":  ("❄️",  "Nieve moderada",                    "text-cyan-400"),
    "73":  ("❄️",  "Nieve abundante",                   "text-cyan-500"),
    "74":  ("❄️",  "Nieve muy abundante",               "text-cyan-600"),
}

WIND_DIRS: dict[str, tuple[str, int]] = {
    "C":  ("Calma",    0),
    "N":  ("Norte",    0),
    "NE": ("Noreste",  45),
    "E":  ("Este",     90),
    "SE": ("Sureste",  135),
    "S":  ("Sur",      180),
    "SO": ("Suroeste", 225),
    "O":  ("Oeste",    270),
    "NO": ("Noroeste", 315),
}

ALERT_COLORS: dict[str, str] = {
    "verde":    "bg-green-100  dark:bg-green-900  border-green-400  text-green-800  dark:text-green-200",
    "amarillo": "bg-yellow-100 dark:bg-yellow-900 border-yellow-400 text-yellow-800 dark:text-yellow-200",
    "naranja":  "bg-orange-100 dark:bg-orange-900 border-orange-400 text-orange-800 dark:text-orange-200",
    "rojo":     "bg-red-100    dark:bg-red-900    border-red-500    text-red-800    dark:text-red-200",
}


def _aemet_fetch(endpoint: str) -> dict | list | None:
    """Llama al endpoint AEMET (paso 1: obtener datos URL; paso 2: descargar)."""
    if not settings.AEMET_API_KEY:
        logger.warning("forecast: AEMET_API_KEY no configurada")
        return None
    try:
        r1 = requests.get(
            f"{AEMET_BASE}{endpoint}",
            params={"api_key": settings.AEMET_API_KEY},
            timeout=10,
        )
        r1.raise_for_status()
        datos_url = r1.json().get("datos")
        if not datos_url:
            return None
        r2 = requests.get(datos_url, timeout=10)
        r2.raise_for_status()
        return r2.json()
    except Exception as exc:
        logger.error("forecast: error AEMET endpoint=%s exc=%s", endpoint, exc)
        return None


def _sky(code: str | None) -> tuple[str, str, str]:
    if not code:
        return ("🌡️", "Sin datos", "text-slate-400")
    return SKY_STATES.get(str(code), ("🌡️", str(code), "text-slate-400"))


def _wind(entries: list[dict]) -> tuple[str, int, int, int]:
    """Extrae dirección y velocidad medias del día. Devuelve (dir_label, dir_deg, vel_km, racha_km)."""
    if not entries:
        return ("—", 0, 0, 0)
    # Tomar la entrada del período más representativo (todo el día si existe)
    entry = next((e for e in entries if e.get("periodo") in ("", "00-24", None)), entries[0])
    direccion = entry.get("direccion", ["C"])
    velocidad = entry.get("velocidad", [0])
    dir_code = direccion[0] if isinstance(direccion, list) else direccion
    vel = int(velocidad[0]) if isinstance(velocidad, list) else int(velocidad or 0)
    dir_label, dir_deg = WIND_DIRS.get(str(dir_code), ("—", 0))
    return (dir_label, dir_deg, vel, 0)


def get_forecast() -> list[dict]:
    cached = cache.get("aemet_forecast_v2")
    if cached is not None:
        return cached

    raw = _aemet_fetch(f"/prediccion/especifica/municipio/diaria/{MUNICIPIO}")
    if not raw:
        return []

    try:
        dias_raw: list[dict] = raw[0]["prediccion"]["dia"]
    except (IndexError, KeyError, TypeError):
        logger.error("forecast: estructura inesperada en respuesta AEMET")
        return []

    result: list[dict] = []
    today = date.today()

    for dia in dias_raw:
        try:
            fecha_str: str = dia.get("fecha", "")[:10]
            fecha = date.fromisoformat(fecha_str)

            # Temperatura
            temp_max = dia.get("temperatura", {}).get("maxima")
            temp_min = dia.get("temperatura", {}).get("minima")
            feels_max = dia.get("sensTermica", {}).get("maxima")
            feels_min = dia.get("sensTermica", {}).get("minima")

            # Precipitación — primer período disponible (todo el día)
            prob_entries = dia.get("probPrecipitacion", [])
            prob_precip = _first_value(prob_entries, 0)

            precip_entries = dia.get("precipitacion", [])
            precip_mm = _first_value(precip_entries, 0)

            # Tormenta y nieve
            prob_tormenta = _first_value(dia.get("probTormenta", []), 0)
            prob_nieve = _first_value(dia.get("probNieve", []), 0)

            # Cielo — período diurno (valor sin sufijo "n")
            cielo_entries = dia.get("estadoCielo", [])
            sky_code = _first_day_sky(cielo_entries)
            emoji, sky_desc, sky_class = _sky(sky_code)

            # Viento
            viento_entries = dia.get("viento", [])
            dir_label, dir_deg, vel_km, _ = _wind(viento_entries)

            racha_entries = dia.get("rachaMax", [])
            racha_km = _first_value(racha_entries, 0)

            # UV
            uv_max = dia.get("uvMax", None)

            # Humedad
            hum_max = dia.get("humedadRelativa", {}).get("maxima")
            hum_min = dia.get("humedadRelativa", {}).get("minima")

            result.append({
                "fecha":        fecha,
                "fecha_str":    fecha_str,
                "dia_semana":   DIAS_ES[fecha.weekday()],
                "dia_num":      fecha.day,
                "mes":          MESES_ES[fecha.month],
                "es_hoy":       fecha == today,
                "temp_max":     temp_max,
                "temp_min":     temp_min,
                "feels_max":    feels_max,
                "feels_min":    feels_min,
                "hum_max":      hum_max,
                "hum_min":      hum_min,
                "prob_precip":  prob_precip,
                "precip_mm":    precip_mm,
                "prob_tormenta": prob_tormenta,
                "prob_nieve":   prob_nieve,
                "sky_code":     sky_code,
                "sky_emoji":    emoji,
                "sky_desc":     sky_desc,
                "sky_class":    sky_class,
                "viento_dir":   dir_label,
                "viento_deg":   dir_deg,
                "viento_km":    vel_km,
                "racha_km":     int(racha_km) if racha_km else 0,
                "uv_max":       uv_max,
            })
        except Exception as exc:
            logger.warning("forecast: error procesando día %s: %s", dia.get("fecha"), exc)
            continue

    cache.set("aemet_forecast_v2", result, CACHE_TTL)
    return result


def _aemet_datos_url(endpoint: str) -> str | None:
    """Solo paso 1: devuelve la URL 'datos' sin descargar su contenido.
    Útil para productos binarios como el radar (imagen PNG/GIF)."""
    if not settings.AEMET_API_KEY:
        return None
    try:
        r = requests.get(
            f"{AEMET_BASE}{endpoint}",
            params={"api_key": settings.AEMET_API_KEY},
            timeout=10,
        )
        r.raise_for_status()
        return r.json().get("datos")
    except Exception as exc:
        logger.warning("forecast: no se pudo obtener datos_url endpoint=%s exc=%s", endpoint, exc)
        return None


def get_radar_url() -> str | None:
    cached = cache.get("aemet_radar_url")
    if cached is not None:
        return cached

    # Intentar radar regional Suroeste (cubre Extremadura); si falla, nacional
    url = _aemet_datos_url("/red/radar/regional/sw")
    if not url:
        url = _aemet_datos_url("/red/radar/nacional")

    if url:
        cache.set("aemet_radar_url", url, 600)  # 10 min — el radar se renueva cada ~10 min
    return url


def get_alerts() -> list[dict]:
    cached = cache.get("aemet_alerts")
    if cached is not None:
        return cached

    # Endpoint de avisos para Extremadura (area ext)
    raw = _aemet_fetch("/avisos_cap/ultimoelaborado/area/ext")
    alerts: list[dict] = []

    if raw:
        try:
            if isinstance(raw, list):
                for item in raw:
                    nivel = str(item.get("nivel", "")).lower()
                    if nivel and nivel != "verde":
                        alerts.append({
                            "tipo":       item.get("tipo", "Aviso meteorológico"),
                            "nivel":      nivel,
                            "descripcion": item.get("descripcion", ""),
                            "css":        ALERT_COLORS.get(nivel, ALERT_COLORS["amarillo"]),
                        })
        except Exception as exc:
            logger.warning("forecast: error procesando alertas: %s", exc)

    cache.set("aemet_alerts", alerts, CACHE_TTL)
    return alerts


# ── helpers ──────────────────────────────────────────────────────────────────

def _first_value(entries: list[dict], default):
    """Devuelve el primer valor numérico de una lista de períodos AEMET."""
    if not entries:
        return default
    # Preferir el período "00-24" (todo el día)
    for e in entries:
        if e.get("periodo") in ("00-24", "", None):
            v = e.get("value") or e.get("valor")
            return v if v is not None else default
    v = entries[0].get("value") or entries[0].get("valor")
    return v if v is not None else default


def _first_day_sky(entries: list[dict]) -> str | None:
    """Devuelve el código de cielo diurno más representativo del día."""
    if not entries:
        return None
    # Preferir el período que no tenga sufijo nocturno
    for e in entries:
        val = str(e.get("value", "")).strip()
        if val and not val.endswith("n"):
            return val
    # Si solo hay nocturnos, devolver el primero
    return str(entries[0].get("value", "")).strip() or None
