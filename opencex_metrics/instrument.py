import logging, time
log = logging.getLogger("opencex_metrics.instrument")

def install():
    try:
        import opencex_swap_api.keeper as km
    except ImportError:
        return
    orig = km.SwapKeeper.execute
    def execute_instrumented(self, plan, user_id, sell_symbol, buy_symbol):
        from opencex_metrics.registry import observe_keeper, observe_swap
        chain_id = int(plan.get("chain_id") or 1)
        t0 = time.perf_counter()
        result = orig(self, plan, user_id, sell_symbol, buy_symbol)
        elapsed = time.perf_counter() - t0
        observe_swap(chain_id, "success" if result.success else "failed", elapsed)
        observe_keeper(chain_id, "success" if result.success else (result.error or "error"),
                       lock_failed=(result.error == "insufficient_balance_or_lock_failed"))
        return result
    km.SwapKeeper.execute = execute_instrumented
    log.info("metrics instrumented")
