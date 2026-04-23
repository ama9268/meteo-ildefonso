from rest_framework.routers import DefaultRouter

from .views import AlertRuleViewSet

router = DefaultRouter()
router.register(r"alerts", AlertRuleViewSet, basename="alert")

urlpatterns = router.urls
