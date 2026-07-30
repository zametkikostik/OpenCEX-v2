# Wire into OpenCEX-backend

```python
from opencex_django.settings_patch import apply_opencex_v2
apply_opencex_v2(globals())

from opencex_django.urls_patch import opencex_v2_urlpatterns
urlpatterns += opencex_v2_urlpatterns
```

```bash
python manage.py migrate opencex_django
celery -A exchange worker -l info
```

Balance: OPENCEX_BALANCE_HOOKS -> BalanceManager set_hold / free_hold / increase_amount
KYC: KYC_SWAP_THRESHOLD_USD, KYCRequiredForWithdraw
Limits: OPENCEX_SWAP_LIMITS

Full: integration/OPEN_CEX_BACKEND.md
