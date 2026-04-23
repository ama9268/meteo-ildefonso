from rest_framework import viewsets

from .models import AlertRule
from .serializers import AlertRuleSerializer


class AlertRuleViewSet(viewsets.ModelViewSet):
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
