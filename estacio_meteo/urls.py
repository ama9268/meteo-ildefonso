from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Auth tokens API
    path("api/v1/token/", obtain_auth_token, name="api-token"),
    path("api/v1/jwt/", TokenObtainPairView.as_view(), name="jwt-obtain"),
    path("api/v1/jwt/refresh/", TokenRefreshView.as_view(), name="jwt-refresh"),

    # Apps
    path("", include("apps.ingest.urls")),
    path("", include("apps.dashboard.urls")),
    path("", include("apps.forecast.urls")),
    path("api/v1/", include("apps.alerts.urls")),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
