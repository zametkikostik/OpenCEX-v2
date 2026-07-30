from django.http import HttpResponse
from .registry import CONTENT_TYPE, generate_latest

def metrics_view(request):
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE)
