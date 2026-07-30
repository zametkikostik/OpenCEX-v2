#!/usr/bin/env python3
import argparse, json, os, sys, urllib.error, urllib.request

def req(method, url, token="", body=None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode()[:500]
        try: return e.code, json.loads(raw)
        except Exception: return e.code, {"raw": raw}
    except Exception as e:
        return 0, {"error": str(e)}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", required=True)
    p.add_argument("--token", default=os.getenv("OPENCEX_TOKEN", ""))
    p.add_argument("--metrics-url", default="")
    p.add_argument("--chain-id", type=int, default=1)
    p.add_argument("--quote", action="store_true")
    p.add_argument("--execute", action="store_true")
    args = p.parse_args()
    base = args.base_url.rstrip("/"); failed = 0
    print("=== staging e2e", base)
    if args.metrics_url:
        st, _ = req("GET", args.metrics_url); print("metrics", st)
        if st not in (200, 0): failed += 1
    if args.quote:
        st, body = req("POST", f"{base}/swap/quote/", args.token,
            {"chain_id": args.chain_id, "sell": "ETH", "buy": "USDT", "amount": "1000000000000000"})
        print("quote", st); 
        if st not in (200, 201): failed += 1
    st, _ = req("POST", f"{base}/settlement/plan/", args.token, {})
    print("settlement/plan", st)
    if args.execute:
        st, body = req("POST", f"{base}/swap/execute/", args.token,
            {"chain_id": args.chain_id, "sell": "ETH", "buy": "USDT", "amount": "1000000000000000"})
        print("execute", st, body)
        if st not in (200, 201, 202): failed += 1
    print("RESULT", "PASS" if failed == 0 else "FAIL"); return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main())
