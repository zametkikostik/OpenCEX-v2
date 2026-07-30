# Custody Runbook

Vault/KMS only for keepers. Fee treasury = multi-sig Safe.
Rotation: new key → Vault → rolling restart → drain old.
Compromise: CIRCUIT_BREAKER=1, move funds, rotate, post-mortem.
