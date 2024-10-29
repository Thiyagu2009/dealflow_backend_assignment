from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Payment Link Manager API",
        default_version='v1',
        description="API for managing payment links and analytics",
        contact=openapi.Contact(email="thiyagu.nataraj@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)
