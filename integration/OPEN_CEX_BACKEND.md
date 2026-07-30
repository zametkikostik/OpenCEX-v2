# Deploy OpenCEX-v2 into OpenCEX-backend

```python
from opencex_django.settings_patch import apply_opencex_v2
apply_opencex_v2(globals())

from opencex_django.urls_patch import opencex_v2_urlpatterns
urlpatterns += opencex_v2_urlpatterns
```

```bash
pip install -e /path/to/OpenCEX-v2
python manage.py migrate opencex_django
celery -A exchange worker -l info
```

Env: ZEROX_API_KEY, ETH_KEEPER_PRIVATE_KEY, PRIVATE_RPC_URL, ZKME_*, SWAP_MAX_SELL_USD, KYC_SWAP_THRESHOLD_USD

NC = user wallet. Custodial = BalanceManager + keeper.

Proprietary Commercial.
