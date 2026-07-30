from django.urls import include, path

opencex_v2_urlpatterns = [
    path("api/v1/swap/", include("opencex_swap_api.urls")),
    path("api/v1/swap/", include("opencex_django.urls")),
    path("api/v1/kyc/", include("opencex_kyc.django_urls")),
    path("api/v1/wallet/", include("opencex_wallet.django_urls")),
]
