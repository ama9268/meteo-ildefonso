"""
Comando de desarrollo: rellena la base de datos con lecturas meteorológicas
aleatorias pero realistas para Segura de León (Badajoz).

Uso:
    python manage.py seed_data                  # último año, cada 15 min
    python manage.py seed_data --days 90        # últimos 90 días
    python manage.py seed_data --interval 30    # una lectura cada 30 min
    python manage.py seed_data --clear          # borra datos existentes primero
"""
from __future__ import annotations

import math
import random
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand
from django.utils.timezone import now

from apps.ingest.models import WeatherReading

# ── Parámetros climáticos de Segura de León (clima mediterráneo continental) ──
# Temperatura base mensual (°C) — máxima media del mes
TEMP_MAX_MES = [10, 12, 16, 19, 24, 31, 36, 36, 29, 22, 15, 11]
TEMP_MIN_MES = [ 2,  3,  5,  8, 12, 17, 21, 21, 17, 12,  6,  3]

# Humedad base mensual (%) — más húmedo en invierno/primavera
HUM_MES = [68, 62, 55, 55, 50, 35, 25, 26, 38, 58, 68, 72]

# Probabilidad de lluvia por mes (0-1) — típico mediterráneo
PROB_LLUVIA_MES = [0.10, 0.10, 0.12, 0.12, 0.08, 0.02, 0.01, 0.01, 0.06, 0.12, 0.12, 0.10]

# Viento base mensual (km/h)
VIENTO_MES = [12, 14, 16, 14, 12, 10, 8, 8, 10, 12, 14, 13]

STATION_ID = "IES_ILDEFONSO"
BATCH = 500  # lecturas por INSERT


class Command(BaseCommand):
    help = "Genera lecturas meteorológicas de prueba para desarrollo"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=365,
                            help="Días de historial a generar (default: 365)")
        parser.add_argument("--interval", type=int, default=15,
                            help="Minutos entre lecturas (default: 15)")
        parser.add_argument("--clear", action="store_true",
                            help="Borra todos los datos existentes antes de insertar")

    def handle(self, *args, **options):
        days = options["days"]
        interval = options["interval"]

        if options["clear"]:
            count, _ = WeatherReading.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Borradas {count} lecturas existentes."))

        total_readings = (days * 24 * 60) // interval
        self.stdout.write(
            f"Generando {total_readings:,} lecturas "
            f"({days} días, cada {interval} min)…"
        )

        # Desactivar auto_now_add para poder fijar received_at manualmente
        field = WeatherReading._meta.get_field("received_at")
        field.auto_now_add = False

        try:
            end_dt = now()
            start_dt = end_dt - timedelta(days=days)

            batch: list[WeatherReading] = []
            inserted = 0

            # Estado de lluvia (persiste entre lecturas del mismo día)
            rain_daily_acc = 0.0
            current_day = None

            ts = start_dt
            while ts <= end_dt:
                day = ts.date()

                # Reiniciar lluvia acumulada al cambiar de día
                if day != current_day:
                    current_day = day
                    # Decidir si llueve hoy (según probabilidad mensual)
                    mes_idx = day.month - 1
                    llueve_hoy = random.random() < PROB_LLUVIA_MES[mes_idx]
                    # mm totales del día si llueve (distribución exponencial)
                    lluvia_dia_total = (
                        max(0.2, random.expovariate(1 / 8)) if llueve_hoy else 0.0
                    )
                    rain_daily_acc = 0.0

                r = _generate_reading(ts, rain_daily_acc, lluvia_dia_total)
                rain_daily_acc = r.rain_daily  # actualizar acumulado

                batch.append(r)

                if len(batch) >= BATCH:
                    WeatherReading.objects.bulk_create(batch)
                    inserted += len(batch)
                    batch = []
                    self.stdout.write(f"  … {inserted:,} / {total_readings:,}", ending="\r")
                    self.stdout.flush()

                ts += timedelta(minutes=interval)

            if batch:
                WeatherReading.objects.bulk_create(batch)
                inserted += len(batch)

        finally:
            field.auto_now_add = True  # Restaurar siempre, aunque haya error

        self.stdout.write("")  # salto de línea tras el \r
        self.stdout.write(self.style.SUCCESS(
            f"OK: {inserted:,} lecturas insertadas correctamente."
        ))


# ── Generación de una lectura ─────────────────────────────────────────────────

def _solar_factor(hour_utc: float, mes: int) -> float:
    """0.0 (noche) → 1.0 (mediodía verano). Hora en UTC+2 aprox."""
    hora_local = (hour_utc + 2) % 24  # España verano ≈ UTC+2
    # Orto y ocaso aproximados según mes (Segura de León, lat 38°N)
    # Formato [orto, ocaso] en hora local
    orto_ocaso = [
        (8.0, 18.5), (7.5, 19.2), (7.0, 20.0), (7.0, 21.0),
        (7.0, 21.5), (7.0, 22.0), (7.2, 22.0), (7.5, 21.5),
        (7.8, 20.5), (8.0, 19.5), (7.5, 18.5), (8.0, 18.2),
    ]
    orto, ocaso = orto_ocaso[mes]
    if hora_local <= orto or hora_local >= ocaso:
        return 0.0
    mitad = (orto + ocaso) / 2
    # Curva senoidal centrada en el mediodía solar
    angle = math.pi * (hora_local - orto) / (ocaso - orto)
    return max(0.0, math.sin(angle))


def _generate_reading(ts: datetime, rain_acc: float, lluvia_total: float) -> WeatherReading:
    mes = ts.month - 1  # 0-11
    hour = ts.hour + ts.minute / 60.0

    # ── Temperatura ──────────────────────────────────────────────
    t_max = TEMP_MAX_MES[mes]
    t_min = TEMP_MIN_MES[mes]
    # Ciclo diario: mínima a las 6h, máxima a las 14h (hora local ≈ UTC+2)
    hora_local = (hour + 2) % 24
    ciclo = math.cos(math.pi * (hora_local - 14) / 12)  # 1 en las 14h, -1 en las 2h
    t_base = (t_max + t_min) / 2 + (t_max - t_min) / 2 * ciclo
    temp_out = round(t_base + random.gauss(0, 1.2), 1)
    temp_in = round(temp_out + random.uniform(1.5, 4.0), 1)

    # ── Humedad ──────────────────────────────────────────────────
    hum_base = HUM_MES[mes]
    # Más húmedo por la mañana, más seco por la tarde
    hum_ciclo = -ciclo * 8  # inverso al ciclo de temperatura
    hum = int(max(10, min(100, hum_base + hum_ciclo + random.gauss(0, 5))))

    # ── Presión ──────────────────────────────────────────────────
    # Paseo aleatorio lento; se reinicia implícitamente cada lectura con gauss pequeño
    pres = round(1013.0 + random.gauss(0, 8), 1)
    pres = max(980.0, min(1035.0, pres))

    # ── Viento ───────────────────────────────────────────────────
    v_base = VIENTO_MES[mes]
    wind = max(0.0, round(random.gauss(v_base, v_base * 0.5), 1))
    # Rachas: 20-80% más que la velocidad media
    wind_gust = round(wind * random.uniform(1.2, 1.8), 1) if wind > 0 else 0.0
    wind_dir = random.choice([0, 45, 90, 135, 180, 225, 270, 315])

    # ── Lluvia ───────────────────────────────────────────────────
    sol = _solar_factor(hour, mes)
    if lluvia_total > 0:
        # Distribuir la lluvia del día a lo largo de las horas de lluvia
        # (preferiblemente por la mañana o tarde, no en el pico de calor)
        peso = max(0, 1 - sol * 0.7) + 0.1  # menos lluvia en horas de sol fuerte
        incremento = lluvia_total * peso * (15 / (24 * 60)) * random.uniform(0, 2)
        nuevo_acc = round(min(lluvia_total, rain_acc + incremento), 1)
        rain_rate = round(incremento * 4, 2)  # mm/15min → mm/h aprox
    else:
        nuevo_acc = rain_acc
        rain_rate = 0.0

    # ── Radiación solar y UV ──────────────────────────────────────
    # Potencia máxima varía con el mes (verano más intenso)
    sol_max = [650, 750, 900, 1000, 1050, 1100, 1100, 1050, 950, 850, 700, 600][mes]
    nubes = random.uniform(0.3, 1.0)  # factor nubosidad
    solar = round(sol * sol_max * nubes + random.gauss(0, 10), 1)
    solar = max(0.0, solar)

    uv_max_mes = [2, 3, 5, 6, 8, 10, 11, 10, 7, 5, 3, 2][mes]
    uv = round(sol * uv_max_mes * nubes + random.gauss(0, 0.3), 1)
    uv = max(0.0, uv)

    reading = WeatherReading(
        station_id=STATION_ID,
        received_at=ts,
        temperature_out=temp_out,
        temperature_in=temp_in,
        humidity_out=float(hum),
        humidity_in=float(max(30, min(95, hum + random.randint(-5, 5)))),
        pressure=pres,
        wind_speed=wind,
        wind_gust=wind_gust,
        wind_dir=float(wind_dir),
        rain_rate=rain_rate,
        rain_daily=nuevo_acc,
        uv_index=uv,
        solar_radiation=solar,
        raw_payload={"seed": True},
    )
    # Guardar el acumulado de lluvia en el objeto para que el bucle lo lea
    reading.rain_daily = nuevo_acc
    return reading
