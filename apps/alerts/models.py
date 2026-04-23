from __future__ import annotations

from django.db import models


class AlertRule(models.Model):
    OPERATORS = [
        ("gt", "Mayor que (>)"),
        ("lt", "Menor que (<)"),
        ("gte", "Mayor o igual (>=)"),
        ("lte", "Menor o igual (<=)"),
    ]

    FIELD_CHOICES = [
        ("temperature_out", "Temperatura exterior (°C)"),
        ("temperature_in", "Temperatura interior (°C)"),
        ("humidity_out", "Humedad exterior (%)"),
        ("humidity_in", "Humedad interior (%)"),
        ("pressure", "Presión (hPa)"),
        ("wind_speed", "Velocidad del viento (km/h)"),
        ("wind_gust", "Ráfaga de viento (km/h)"),
        ("rain_rate", "Tasa de lluvia (mm/h)"),
        ("rain_daily", "Lluvia diaria (mm)"),
        ("uv_index", "Índice UV"),
    ]

    name = models.CharField(max_length=128)
    field = models.CharField(max_length=32, choices=FIELD_CHOICES)
    operator = models.CharField(max_length=4, choices=OPERATORS)
    threshold = models.FloatField()
    email_to = models.EmailField()
    active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name}: {self.field} {self.operator} {self.threshold}"
