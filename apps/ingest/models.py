from __future__ import annotations

import math

from django.db import models


class WeatherReading(models.Model):
    station_id = models.CharField(max_length=64, db_index=True)
    received_at = models.DateTimeField(auto_now_add=True, db_index=True)

    temperature_out = models.FloatField(null=True, blank=True)
    temperature_in = models.FloatField(null=True, blank=True)
    humidity_out = models.FloatField(null=True, blank=True)
    humidity_in = models.FloatField(null=True, blank=True)
    pressure = models.FloatField(null=True, blank=True)
    wind_speed = models.FloatField(null=True, blank=True)
    wind_gust = models.FloatField(null=True, blank=True)
    wind_dir = models.FloatField(null=True, blank=True)
    rain_rate = models.FloatField(null=True, blank=True)
    rain_daily = models.FloatField(null=True, blank=True)
    uv_index = models.FloatField(null=True, blank=True)
    solar_radiation = models.FloatField(null=True, blank=True)

    raw_payload = models.JSONField(default=dict)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["station_id", "received_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.station_id} @ {self.received_at:%Y-%m-%d %H:%M:%S}"

    @property
    def feels_like(self) -> float | None:
        t = self.temperature_out
        if t is None:
            return None

        v = self.wind_speed or 0.0
        h = self.humidity_out or 0.0

        if t <= 10.0 and v >= 4.8:
            # Wind chill (Environment Canada / Steadman)
            wc = (13.12 + 0.6215 * t
                  - 11.37 * math.pow(v, 0.16)
                  + 0.3965 * t * math.pow(v, 0.16))
            return round(wc, 1)

        if t >= 27.0 and h >= 40.0:
            # Heat index NWS Rothfusz (convertido a °C)
            hi = (-8.78469475556
                  + 1.61139411 * t
                  + 2.33854883889 * h
                  - 0.14611605 * t * h
                  - 0.012308094 * t ** 2
                  - 0.0164248277778 * h ** 2
                  + 0.002211732 * t ** 2 * h
                  + 0.00072546 * t * h ** 2
                  - 0.000003582 * t ** 2 * h ** 2)
            return round(hi, 1)

        return round(t, 1)
