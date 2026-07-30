# Staging Deploy Checklist

1. pip install -e OpenCEX-v2
2. apply_opencex_v2(globals()) + urlpatterns
3. .env.staging chmod 600
4. migrate opencex_django
5. celery worker + CELERY_IMPORTS
6. smoke + staging_e2e.py
7. docker compose observability
8. Go/No-go: quote, NC UI, execute queue, metrics
