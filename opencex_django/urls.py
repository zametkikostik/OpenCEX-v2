from django.urls import path
from opencex_django.views_execute import SwapExecuteAsyncView, SwapExecutionStatusView

urlpatterns = [
    path("execute/", SwapExecuteAsyncView.as_view(), name="swap_execute_async"),
    path("execution/<int:execution_id>/", SwapExecutionStatusView.as_view(), name="swap_execution_status"),
]
