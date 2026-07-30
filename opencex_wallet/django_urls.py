from django.urls import path
from .django_api import NonCustodialSwapView, OrderBuildView, OrderSubmitView, WalletSessionView

app_name = "opencex_wallet"

urlpatterns = [
    path("session/", WalletSessionView.as_view(), name="session"),
    path("order/build/", OrderBuildView.as_view(), name="order_build"),
    path("order/submit/", OrderSubmitView.as_view(), name="order_submit"),
    path("swap/nc/", NonCustodialSwapView.as_view(), name="swap_nc"),
]
