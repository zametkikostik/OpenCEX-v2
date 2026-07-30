# OpenCEX-v2 status v0.9.0

## Done
1. Backend integration: settings_patch, urls_patch, OPEN_CEX_BACKEND.md
2. Balance hooks: decimals, lock/unlock/credit + sell-side spend_hold
3. Keeper limits + MEV private RPC + credit with sell kwargs
4. KYC gates on withdraw/swap execute
5. E2E tests: 12 passed

## Wire
```python
from opencex_django.settings_patch import apply_opencex_v2
apply_opencex_v2(globals())
from opencex_django.urls_patch import opencex_v2_urlpatterns
urlpatterns += opencex_v2_urlpatterns
```

## Remaining (ops)
HSM keys, testnet smoke, Prometheus, on-chain NC settlement, ERC-4337
