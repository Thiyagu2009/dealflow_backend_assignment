"""
URL configuration for dealflow project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings

from payments.views import analytics_views, payment_views, stripe_webhooks
from .docs import schema_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('payments.urls')),
    path('payment/completed/', payment_views.payment_completed, name='payment-success'),
    path('payment/<str:payment_id>/', payment_views.payment_page, name='payment-page'),
    path('webhooks/stripe/', stripe_webhooks.stripe_webhook, name='stripe-webhook'),
    path('api/docs/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('', analytics_views.health_check, name='health-check'),
]+ static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
