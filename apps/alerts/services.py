from __future__ import annotations

import logging
import operator as op
from typing import TYPE_CHECKING

from django.core.mail import send_mail
from django.utils import timezone

if TYPE_CHECKING:
    from apps.ingest.models import WeatherReading

logger = logging.getLogger(__name__)

_OPS = {
    "gt": op.gt,
    "lt": op.lt,
    "gte": op.ge,
    "lte": op.le,
}


def check_alerts(reading: WeatherReading) -> None:
    from .models import AlertRule

    rules = AlertRule.objects.filter(active=True)
    for rule in rules:
        value = getattr(reading, rule.field, None)
        if value is None:
            continue
        comparator = _OPS.get(rule.operator)
        if comparator is None:
            continue
        if comparator(value, rule.threshold):
            _send_alert(rule, reading, value)


def _send_alert(rule, reading: WeatherReading, value: float) -> None:
    subject = f"[EstacioMeteo] Alerta: {rule.name}"
    body = (
        f"La regla '{rule.name}' se ha disparado.\n\n"
        f"  Campo: {rule.field}\n"
        f"  Valor actual: {value}\n"
        f"  Condición: {rule.operator} {rule.threshold}\n"
        f"  Estación: {reading.station_id}\n"
        f"  Fecha/hora: {reading.received_at}\n"
    )
    try:
        send_mail(subject, body, None, [rule.email_to], fail_silently=False)
        rule.last_triggered = timezone.now()
        rule.save(update_fields=["last_triggered"])
        logger.info("alerts: alerta '%s' enviada a %s", rule.name, rule.email_to)
    except Exception as exc:
        logger.error("alerts: error enviando alerta '%s': %s", rule.name, exc)
