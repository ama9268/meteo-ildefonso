from django.contrib import admin

from .models import WeatherReading


@admin.register(WeatherReading)
class WeatherReadingAdmin(admin.ModelAdmin):
    list_display = [
        "station_id", "received_at", "temperature_out", "humidity_out",
        "pressure", "wind_speed", "rain_daily",
    ]
    list_filter = ["station_id"]
    date_hierarchy = "received_at"
    readonly_fields = ["raw_payload", "received_at"]
    search_fields = ["station_id"]
