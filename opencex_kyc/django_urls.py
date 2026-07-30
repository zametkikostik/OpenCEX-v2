from django.urls import path

from .django_api import (
    KYCProvidersView,
    KYCRefreshView,
    KYCStartView,
    KYCStatusView,
    KYCWebhookView,
)

app_name = "opencex_kyc"

urlpatterns = [
    path("start/", KYCStartView.as_view(), name="start"),
    path("status/", KYCStatusView.as_view(), name="status"),
    path("refresh/", KYCRefreshView.as_view(), name="refresh"),
    path("providers/", KYCProvidersView.as_view(), name="providers"),
    path("webhook/<str:provider>/", KYCWebhookView.as_view(), name="webhook"),
]
