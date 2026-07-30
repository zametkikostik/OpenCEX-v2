from __future__ import annotations
import logging, os, time
from contextlib import contextmanager
from typing import Iterator, Optional
log = logging.getLogger("opencex_metrics")
_AVAILABLE = False
try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest as _generate_latest, start_http_server, CONTENT_TYPE_LATEST
    _AVAILABLE = True
    _RPC_LATENCY = Histogram("opencex_rpc_latency_seconds", "RPC latency", ["chain_id", "provider", "method"], buckets=(0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10))
    _RPC_ERRORS = Counter("opencex_rpc_errors_total", "RPC errors", ["chain_id", "provider", "error_type"])
    _RPC_REQUESTS = Counter("opencex_rpc_requests_total", "RPC requests", ["chain_id", "provider", "method", "status"])
    _SWAP_QUOTES = Counter("opencex_swap_quotes_total", "Quotes", ["chain_id", "sell", "buy", "source", "status"])
    _SWAP_EXEC = Counter("opencex_swap_executions_total", "Executions", ["chain_id", "status"])
    _SWAP_LATENCY = Histogram("opencex_swap_execution_seconds", "Swap duration", ["chain_id"], buckets=(1, 5, 15, 30, 60, 120, 300))
    _KEEPER_TX = Counter("opencex_keeper_tx_total", "Keeper txs", ["chain_id", "result"])
    _KEEPER_LOCK_FAIL = Counter("opencex_keeper_lock_fail_total", "Lock fails", ["chain_id"])
    _KYC_STATUS = Counter("opencex_kyc_events_total", "KYC events", ["provider", "status"])
    _PROVIDER_HEALTH = Gauge("opencex_rpc_provider_healthy", "Provider health", ["chain_id", "provider"])
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain"
    def _generate_latest(): return b"# no prometheus_client\n"
    def start_http_server(port): pass

def metrics_available(): return _AVAILABLE

def observe_rpc(chain_id, provider, method, status="ok", latency_sec=None, error_type=None):
    if not _AVAILABLE: return
    _RPC_REQUESTS.labels(chain_id=str(chain_id), provider=provider or "unknown", method=method or "unknown", status=status).inc()
    if latency_sec is not None: _RPC_LATENCY.labels(chain_id=str(chain_id), provider=provider or "unknown", method=method or "unknown").observe(latency_sec)
    if error_type: _RPC_ERRORS.labels(chain_id=str(chain_id), provider=provider or "unknown", error_type=error_type).inc()

def set_provider_health(chain_id, provider, healthy):
    if _AVAILABLE: _PROVIDER_HEALTH.labels(chain_id=str(chain_id), provider=provider).set(1 if healthy else 0)

def observe_swap_quote(chain_id, sell, buy, source="0x", status="ok"):
    if _AVAILABLE: _SWAP_QUOTES.labels(chain_id=str(chain_id), sell=sell.upper(), buy=buy.upper(), source=source, status=status).inc()

def observe_swap(chain_id, status, latency_sec=None):
    if not _AVAILABLE: return
    _SWAP_EXEC.labels(chain_id=str(chain_id), status=status).inc()
    if latency_sec is not None: _SWAP_LATENCY.labels(chain_id=str(chain_id)).observe(latency_sec)

def observe_keeper(chain_id, result, lock_failed=False):
    if not _AVAILABLE: return
    _KEEPER_TX.labels(chain_id=str(chain_id), result=result).inc()
    if lock_failed: _KEEPER_LOCK_FAIL.labels(chain_id=str(chain_id)).inc()

def observe_kyc(provider, status):
    if _AVAILABLE: _KYC_STATUS.labels(provider=provider or "unknown", status=status).inc()

@contextmanager
def timed_rpc(chain_id, provider, method):
    t0 = time.perf_counter(); err = None
    try: yield
    except Exception as e:
        err = type(e).__name__; raise
    finally:
        observe_rpc(chain_id, provider, method, "error" if err else "ok", time.perf_counter()-t0, err)

def start_metrics_server(port=None):
    if not _AVAILABLE: return
    port = int(port or os.getenv("OPENCEX_METRICS_PORT", "9090"))
    start_http_server(port); log.info("metrics on :%s", port)

def generate_latest():
    return _generate_latest() if _AVAILABLE else b"# no metrics\n"

CONTENT_TYPE = CONTENT_TYPE_LATEST
