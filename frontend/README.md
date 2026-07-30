# OpenCEX NC Swap UI — React + Vue + WalletConnect v2

```bash
cd frontend && npm install
# set VITE_WC_PROJECT_ID from cloud.walletconnect.com
npm run dev:react   # or dev:vue
```

## Balance hooks (backend)

```python
from opencex_django.balance_hooks import OPENCEX_BALANCE_HOOKS
# settings.OPENCEX_BALANCE_HOOKS = OPENCEX_BALANCE_HOOKS
```

Uses OpenCEX `BalanceManager.set_hold` / `free_hold` / `increase_amount`.

## License

Proprietary Commercial.
