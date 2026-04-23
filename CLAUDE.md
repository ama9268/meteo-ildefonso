# EstacioMeteo — Documentación del Proyecto

## Descripción

Aplicación Django desplegada en Raspberry Pi que recibe datos periódicos de una estación meteorológica **Bresser 7-en-1 MeteoChamp HD WiFi Weather Center**. La estación envía los datos vía HTTP GET al endpoint `/weather`; el backend valida, almacena en PostgreSQL y expone una API REST autenticada y un dashboard web con gráficas históricas.

Flujo de datos:
```
Bresser 7-en-1  →  GET /weather  →  WeatherReading (PostgreSQL)  →  API /api/v1/  →  Dashboard web
                                                                                  →  Clientes externos
```

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Runtime | Python 3.11 + venv |
| Framework | Django 5.x |
| API REST | Django REST Framework |
| Auth API | DRF Token + JWT (djangorestframework-simplejwt) |
| Base de datos | PostgreSQL + psycopg2-binary |
| Variables entorno | django-environ |
| Gráficas | Chart.js (CDN) en Django Templates |
| Servidor WSGI | Gunicorn |
| Proxy inverso | Nginx |
| Alertas email | Django send_mail |
| Deploy | systemd service en Raspberry Pi |

---

## Estructura del proyecto

```
EstacioMeteo/
├── .env                         # Variables secretas — NO subir a git
├── .env.example                 # Plantilla documentada
├── .gitignore
├── CLAUDE.md                    # Este archivo
├── manage.py
├── requirements.txt
├── requirements-dev.txt
├── Recomendaciones.md           # Registro de mejoras técnicas pendientes/implementadas
├── estacio_meteo/               # Configuración Django
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── ingest/                  # Recepción de datos de la estación
│   │   ├── models.py            # WeatherReading
│   │   ├── views.py             # Endpoint /weather + ViewSets DRF
│   │   ├── serializers.py
│   │   ├── parsers.py           # Conversión unidades Bresser → SI
│   │   ├── urls.py
│   │   └── admin.py
│   ├── dashboard/               # Web con Django Templates + Chart.js
│   │   ├── views.py             # CBVs: DashboardView, HistoryView
│   │   ├── urls.py
│   │   └── templates/dashboard/
│   │       ├── index.html
│   │       └── history.html
│   └── alerts/                  # Reglas de alerta por email
│       ├── models.py            # AlertRule
│       ├── services.py          # check_alerts(reading)
│       ├── admin.py
│       └── urls.py
├── static/
├── templates/
│   └── base.html
└── deploy/
    ├── nginx/estacio-meteo.conf
    └── systemd/estacio-meteo.service
```

---

## Configuración del entorno

### Primera vez (desarrollo)

```bash
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux / Raspberry Pi:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus valores

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Variables `.env` requeridas

```env
SECRET_KEY=genera-con-python-secrets-token-hex-32
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=postgres://user:pass@localhost:5432/estacio_meteo
STATION_ID=mi_estacion
STATION_KEY=clave-aleatoria-minimo-32-chars
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=tu@email.com
EMAIL_HOST_PASSWORD=app-password
DEFAULT_FROM_EMAIL=estacio@tudominio.com
```

### Generar `STATION_KEY` segura

```python
import secrets
print(secrets.token_hex(32))
```

---

## Comandos frecuentes

```bash
# Servidor de desarrollo
python manage.py runserver 0.0.0.0:8000

# Migraciones
python manage.py makemigrations
python manage.py migrate

# Tests
python manage.py test apps/

# Simular envío de la estación
curl "http://localhost:8000/weather?ID=mi_estacion&PASSWORD=clave&tempf=72.5&humidity=65&windspeedmph=5&winddir=180&baromin=29.92&rainin=0&dailyrainin=0&UV=3&solarradiation=250.5"

# Colectar estáticos (producción)
python manage.py collectstatic --noinput
```

---

## Endpoints principales

| Método | URL | Descripción | Auth |
|--------|-----|-------------|------|
| GET | `/weather` | Recepción de datos de la estación | Station ID/KEY |
| GET | `/` | Dashboard web | Login |
| GET | `/history/` | Histórico paginado | Login |
| GET | `/api/v1/readings/` | Listado de lecturas | Token/JWT |
| GET | `/api/v1/readings/latest/` | Última lectura | Token/JWT |
| GET | `/api/v1/readings/export/` | Descarga CSV | Token/JWT |
| GET/POST | `/api/v1/alerts/` | Gestión de reglas de alerta | Token/JWT |
| GET | `/api/v1/readings/chart/` | Datos JSON para gráficas | Token/JWT |
| GET | `/health/` | Health check | No auth |
| ANY | `/admin/` | Panel de administración | Django admin |

---

## Modelo de datos

### `WeatherReading`

| Campo | Tipo | Fuente Bresser |
|-------|------|----------------|
| `station_id` | CharField | `ID` |
| `received_at` | DateTimeField (auto) | Servidor |
| `temperature_out` | FloatField | `tempf` → °C |
| `temperature_in` | FloatField | `indoortempf` → °C |
| `humidity_out` | IntegerField | `humidity` |
| `humidity_in` | IntegerField | `indoorhumidity` |
| `pressure` | FloatField | `baromin` → hPa |
| `wind_speed` | FloatField | `windspeedmph` → km/h |
| `wind_gust` | FloatField | `windgustmph` → km/h |
| `wind_dir` | IntegerField | `winddir` |
| `rain_rate` | FloatField | `rainin` → mm/h |
| `rain_daily` | FloatField | `dailyrainin` → mm |
| `uv_index` | FloatField | `UV` |
| `solar_radiation` | FloatField | `solarradiation` |
| `raw_payload` | JSONField | Payload completo |

### `AlertRule`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `field` | CharField | Campo de WeatherReading a evaluar |
| `operator` | CharField | `gt`, `lt`, `eq` |
| `threshold` | FloatField | Valor de referencia |
| `email_to` | EmailField | Destinatario |
| `active` | BooleanField | Habilitar/deshabilitar |
| `last_triggered` | DateTimeField | Última vez que se disparó |

---

## Despliegue en Raspberry Pi

```bash
# 1. Instalar dependencias del sistema
sudo apt update && sudo apt install -y python3-venv postgresql nginx

# 2. Clonar y configurar
git clone <repo> /home/pi/EstacioMeteo
cd /home/pi/EstacioMeteo
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Editar con valores de producción

# 3. Base de datos
sudo -u postgres createdb estacio_meteo
sudo -u postgres createuser estacio --pwprompt
python manage.py migrate

# 4. Servicio systemd
sudo cp deploy/systemd/estacio-meteo.service /etc/systemd/system/
sudo systemctl enable estacio-meteo
sudo systemctl start estacio-meteo

# 5. Nginx
sudo cp deploy/nginx/estacio-meteo.conf /etc/nginx/sites-available/estacio-meteo
sudo ln -s /etc/nginx/sites-available/estacio-meteo /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Reglas de Desarrollo

### 1. Vistas Django

- Usar siempre **Class-Based Views (CBVs)** con `LoginRequiredMixin` para el dashboard y vistas protegidas.
- No crear Function-Based Views salvo para webhooks o endpoints muy simples (como `/weather` o `/health`).

### 2. Modelos

- Todo modelo debe tener `__str__` definido.
- Usar `db_index=True` o `Meta.indexes` en campos usados en filtros o `order_by`.
- Preferir `FloatField` para mediciones; nunca usar `CharField` para valores numéricos.

### 3. Serializers DRF

- Usar `read_only_fields` explícitamente; no dejar campos implícitamente escribibles.
- Validar rangos físicamente plausibles en `validate_<field>` del serializer.

### 4. Seguridad

- Las credenciales de la estación (`STATION_ID`, `STATION_KEY`) siempre desde `.env`, nunca en el código.
- `STATION_KEY` mínimo 32 caracteres generados con `secrets.token_hex()`.
- El endpoint `/weather` debe tener rate limiting configurado.

### 5. Configuración

- Toda configuración que cambie entre entornos va en `.env`, leída con `django-environ`.
- Nunca commitear `.env`; sí commitear `.env.example` actualizado.

---

## Comportamiento en Planificación

Siempre que se presente un plan de implementación, debe incluirse una sección final **"Recomendaciones para Profesionalizar el Desarrollo"** con estos puntos (solo los relevantes al contexto):

1. **Mejoras de calidad**: type hints, logging estructurado, manejo de errores
2. **Buenas prácticas**: patrones de diseño aplicables, separación de responsabilidades
3. **Seguridad**: validaciones, sanitización de datos, permisos
4. **Rendimiento**: índices DB, caché Redis, queries N+1, paginación
5. **Testing**: qué tests agregar para el cambio propuesto
6. **Deuda técnica**: TODOs relacionados que podrían resolverse con el cambio

Las recomendaciones nuevas se persisten en `Recomendaciones.md` bajo su categoría correspondiente, marcando con `[x]` las implementadas.
