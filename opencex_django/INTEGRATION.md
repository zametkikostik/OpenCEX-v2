# Celery + Django models + NC Swap UI

## Install

```python
INSTALLED_APPS += ["opencex_django"]
CELERY_IMPORTS = ("opencex_django.tasks",)
```

```bash
python manage.py migrate opencex_django
celery -A project worker -l info
```

## Models

UserKYC, WalletSessionRecord, SignedOrderRecord, SwapExecution

## Task

`opencex.execute_swap` via `enqueue_swap(user, plan, sell, buy)`

## NC UI

`static/opencex/nc_swap.html` — MetaMask + 0x quote + user-signed tx

## License

Proprietary Commercial.
