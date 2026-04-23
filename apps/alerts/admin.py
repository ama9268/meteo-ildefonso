from django.contrib import admin

from .models import AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ["name", "field", "operator", "threshold", "email_to", "active", "last_triggered"]
    list_filter = ["active", "field"]
    list_editable = ["active"]
    search_fields = ["name", "email_to"]
