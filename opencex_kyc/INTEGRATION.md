# Phase 3 — Zero-Knowledge KYC

## Providers

| Provider | Role | Env |
|----------|------|-----|
| zkMe | Primary zkKYC + MeID | ZKME_API_KEY, ZKME_APP_ID |
| zkPass | Prove existing Web2 KYC | ZKPASS_API_KEY, ZKPASS_API_SECRET |
| Privado ID | DID + VC ZK proofs | PRIVADO_VERIFIER_URL |

## REST

| Method | Path | Auth |
|--------|------|------|
| POST | /api/v1/kyc/start/ | Login |
| GET | /api/v1/kyc/status/ | Login |
| POST | /api/v1/kyc/refresh/ | Login |
| GET | /api/v1/kyc/providers/ | Public |
| POST | /api/v1/kyc/webhook/<provider>/ | Public |

## Wire

```python
path("api/v1/kyc/", include("opencex_kyc.django_urls")),
```

Exchange stores only status + claims — never raw PII/documents.

## License

Proprietary Commercial.
