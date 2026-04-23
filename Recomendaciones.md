# Recomendaciones para Profesionalizar el Desarrollo

Registro de mejoras técnicas identificadas durante la planificación e implementación del proyecto EstacioMeteo.

- Formato pendiente: `- **Título:** Descripción`
- Formato implementada: `- [x] **Título:** Descripción`

---

## Backend

- **Type hints completos:** Anotar todos los métodos de modelos, serializers, services y views con tipos para análisis estático con mypy.
- **Logging estructurado:** Usar `logging.getLogger(__name__)` en cada módulo; loguear `station_id`, `received_at` y resultado en `/weather`; loguear reglas disparadas en `check_alerts`.
- **Manejo de errores en el parser:** Capturar `ValueError` y `KeyError` al convertir campos del payload Bresser; guardar `raw_payload` siempre aunque fallen conversiones individuales.
- **Service layer:** Mantener `check_alerts()`, conversión de unidades y parseo del payload en módulos `services.py` y `parsers.py` separados de las vistas.
- **`parsers.py` dedicado:** Encapsular conversiones °F→°C, mph→km/h, inHg→hPa en funciones puras testeables.
- **CBVs con LoginRequiredMixin:** Todo el dashboard usa Class-Based Views; solo `/weather` y `/health` son Function-Based Views por su naturaleza de webhook.
- **Soporte multi-estación:** Modelar `Station` como entidad propia (`id`, `name`, `key_hash`) para gestionar varias estaciones sin redeploy.
- **Política de retención de datos:** Management command o cron que borre lecturas con más de N meses para evitar crecimiento indefinido de la tabla.

## Seguridad

- **Rate limiting en `/weather`:** Instalar `django-ratelimit` y limitar requests/minuto por IP para evitar flood o replay attacks.
- **Validación de rangos físicos:** En el serializer, rechazar valores fuera de rango (temp −50..60°C, humedad 0..100%, viento 0..200 km/h) antes de persistir.
- **HTTPS con Let's Encrypt:** Configurar Certbot + Nginx para TLS en producción; la API está accesible desde el exterior.
- **`STATION_KEY` robusta:** Generar con `secrets.token_hex(32)` (64 chars hex); documentar en `.env.example`.

## Rendimiento

- **Índice en `received_at`:** Campo más usado en filtros y `order_by`; agregar `db_index=True` o `Meta.indexes`.
- **Índice compuesto `(station_id, received_at)`:** Prepara para soporte multi-estación sin reescritura del modelo.
- **Caché Redis para `/latest/`:** Cachear la última lectura con TTL igual al intervalo de upload de la estación (~60s).
- **Paginación con cursor:** Usar `CursorPagination` de DRF en lugar de offset para queries eficientes en tablas grandes.
- **Migración a TimescaleDB:** Si el volumen supera ~1M lecturas/mes, la extensión TimescaleDB sobre PostgreSQL mejora queries de series temporales sin cambiar el ORM.

## Testing

- **Test del endpoint `/weather`:** Credenciales correctas (200 + registro creado), credenciales incorrectas (401), payload vacío (400).
- **Test de `check_alerts()`:** Valores sobre umbral (email enviado), bajo umbral (sin email), regla inactiva (sin email).
- **Test de exportación CSV:** Verificar `Content-Disposition`, cabeceras de columna y número de filas en el rango solicitado.
- **Factories con factory_boy:** Generar `WeatherReading` con datos realistas en los tests.

## Infraestructura

- **HTTPS con Certbot:** TLS obligatorio para la API accesible externamente.
- **Monitorización del servicio:** Configurar alertas de systemd o un servicio externo para detectar caídas del proceso Gunicorn en Raspberry Pi.
