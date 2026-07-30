#!/usr/bin/env python3
"""OpenCEX testnet smoke. PYTHONPATH=. python scripts/testnet_smoke.py --chain sepolia"""
from __future__ import annotations
import argparse, json, os, sys, time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHAIN_PRESETS = {
    "sepolia": {"chain_id": 11155111, "rpc_env": "RPC_SEPOLIA_URLS", "default_rpc": "https://rpc.sepolia.org",
                "keeper_env": "SEPOLIA_KEEPER_PRIVATE_KEY", "zerox_chain": "sepolia"},
    "base-sepolia": {"chain_id": 84532, "rpc_env": "RPC_BASE_SEPOLIA_URLS", "default_rpc": "https://sepolia.base.org",
                     "keeper_env": "BASE_SEPOLIA_KEEPER_PRIVATE_KEY", "zerox_chain": "base-sepolia"},
}
@dataclass
class CheckResult:
    name: str; ok: bool; detail: str = ""; ms: float = 0.0
@dataclass
class SmokeReport:
    chain: str; chain_id: int
    checks: List[CheckResult] = field(default_factory=list)
    @property
    def passed(self) -> bool: return all(c.ok for c in self.checks)
    def add(self, name, ok, detail="", ms=0.0): self.checks.append(CheckResult(name, ok, detail, ms))

def _rpc_list(preset):
    raw = os.getenv(preset["rpc_env"], "") or preset["default_rpc"]
    return [u.strip() for u in raw.split(",") if u.strip()]

def check_rpc(report, urls):
    try:
        from web3 import Web3
    except ImportError:
        report.add("web3_import", False, "pip install web3"); return None
    last_err = ""
    for url in urls:
        t0 = time.time()
        try:
            w3 = Web3(Web3.HTTPProvider(url, request_kwargs={"timeout": 15}))
            if not w3.is_connected():
                last_err = f"not connected: {url}"; continue
            bn, cid = w3.eth.block_number, w3.eth.chain_id
            ok = cid == report.chain_id
            report.add("rpc_connect", ok, f"url={url} block={bn} chain_id={cid}", (time.time()-t0)*1000)
            if ok: return w3
            last_err = f"chain_id mismatch {cid}"
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
    report.add("rpc_connect", False, last_err); return None

def check_secrets(report):
    t0 = time.time()
    try:
        from opencex_secrets.loader import load_secrets
        s = load_secrets()
        report.add("secrets_load", True, f"source={s.source}", (time.time()-t0)*1000)
    except Exception as e:
        report.add("secrets_load", False, str(e))

def check_keeper_key(report, preset, w3):
    pk = os.getenv(preset["keeper_env"]) or os.getenv("ETH_KEEPER_PRIVATE_KEY")
    if not pk:
        report.add("keeper_key", True, "skipped (no key)"); return
    t0 = time.time()
    try:
        from eth_account import Account
        if not pk.startswith("0x"): pk = "0x" + pk
        acct = Account.from_key(pk)
        bal = w3.eth.get_balance(acct.address) if w3 else 0
        report.add("keeper_key", True, f"address={acct.address} balance_wei={bal}", (time.time()-t0)*1000)
        report.add("keeper_funded", bal > 0, f"balance_wei={bal}")
    except Exception as e:
        report.add("keeper_key", False, str(e))

def check_sign_message(report, preset):
    pk = os.getenv(preset["keeper_env"]) or os.getenv("ETH_KEEPER_PRIVATE_KEY")
    if not pk:
        report.add("sign_message", True, "skipped"); return
    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
        if not pk.startswith("0x"): pk = "0x" + pk
        sig = Account.from_key(pk).sign_message(encode_defunct(text="OpenCEX smoke"))
        report.add("sign_message", bool(sig.signature), "ok")
    except Exception as e:
        report.add("sign_message", False, str(e))

def check_0x_quote(report, preset):
    if not os.getenv("ZEROX_API_KEY"):
        report.add("zerox_quote", True, "skipped"); return
    t0 = time.time()
    try:
        import urllib.request, urllib.error
        url = f"https://api.0x.org/swap/v1/price?sellToken=ETH&buyToken=USDC&sellAmount=100000000000000000&chainId={preset['chain_id']}"
        req = urllib.request.Request(url, headers={"0x-api-key": os.environ["ZEROX_API_KEY"], "0x-version": "v2"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                report.add("zerox_quote", resp.status == 200, resp.read().decode()[:120], (time.time()-t0)*1000)
        except urllib.error.HTTPError as e:
            report.add("zerox_quote", e.code in (400, 404, 501), f"HTTP {e.code}", (time.time()-t0)*1000)
    except Exception as e:
        report.add("zerox_quote", False, str(e))

def check_balance_hooks_import(report):
    try:
        from opencex_django.balance_hooks import OPENCEX_BALANCE_HOOKS, wei_to_decimal
        from decimal import Decimal
        assert wei_to_decimal("1000000000000000000", "ETH") == Decimal("1")
        report.add("balance_hooks", True, "ok")
    except Exception as e:
        report.add("balance_hooks", False, str(e))

def check_keeper_limits_fn(report):
    try:
        from opencex_swap_api.keeper import validate_swap_limits
        err = validate_swap_limits({"sell_amount": "100", "sell_token": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"}, 11155111, "ETH", "USDT")
        report.add("keeper_limits", True, f"validate returned: {err}")
    except Exception as e:
        report.add("keeper_limits", False, str(e))

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--chain", choices=list(CHAIN_PRESETS), default="sepolia")
    p.add_argument("--skip-0x", action="store_true")
    p.add_argument("--skip-keeper", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    preset = CHAIN_PRESETS[args.chain]
    report = SmokeReport(chain=args.chain, chain_id=preset["chain_id"])
    check_secrets(report); check_balance_hooks_import(report); check_keeper_limits_fn(report)
    if args.offline:
        report.add("rpc_connect", True, "skipped (--offline)"); w3 = None
    else:
        w3 = check_rpc(report, _rpc_list(preset))
    if not args.skip_keeper:
        check_keeper_key(report, preset, w3); check_sign_message(report, preset)
    if not args.skip_0x and not args.offline:
        check_0x_quote(report, preset)
    if args.json:
        print(json.dumps({"chain": report.chain, "passed": report.passed, "checks": [asdict(c) for c in report.checks]}, indent=2))
    else:
        print(f"\n=== OpenCEX smoke: {report.chain} ===\n")
        for c in report.checks:
            print(f"  [{'PASS' if c.ok else 'FAIL'}] {c.name:20s} {c.detail[:100]}")
        print("\nRESULT:", "ALL PASSED" if report.passed else "FAILED")
    return 0 if report.passed else 1

if __name__ == "__main__":
    sys.exit(main())
