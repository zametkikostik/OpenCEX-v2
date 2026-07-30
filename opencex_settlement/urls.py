from django.urls import path
from opencex_settlement.django_api import AAUserOpView, SettlementPlanView
urlpatterns = [
    path("plan/", SettlementPlanView.as_view()),
    path("aa/userop/", AAUserOpView.as_view()),
]
