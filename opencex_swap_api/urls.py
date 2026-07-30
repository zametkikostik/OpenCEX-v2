"""URL routes for OpenCEX Swap API."""

from django.urls import path

from .views import (
    SwapExecuteView,
    SwapPreviewView,
    SwapQuoteView,
    SwapSourcesView,
    SwapTokensView,
)

app_name = "opencex_swap"

urlpatterns = [
    path("preview/", SwapPreviewView.as_view(), name="preview"),
    path("quote/", SwapQuoteView.as_view(), name="quote"),
    path("execute/", SwapExecuteView.as_view(), name="execute"),
    path("tokens/", SwapTokensView.as_view(), name="tokens"),
    path("sources/", SwapSourcesView.as_view(), name="sources"),
]
