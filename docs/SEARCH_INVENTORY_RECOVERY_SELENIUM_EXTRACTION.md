# Search Inventory Recovery Selenium Extraction

Status: tenth helper slice implemented  
Scope: Search Inventory readiness and refresh/menu recovery only

## New boundary

`core/router_modes/search_inventory_recovery_selenium.py` now owns the browser
operations formerly implemented by:

- `CaseLawRouter._is_search_inventory_ready()`;
- `CaseLawRouter.refresh_search_inventory_for_retry()`.

Both router methods retain their signatures as thin compatibility entry points. The
module continues using existing router helpers for tab cleanup, alert acceptance,
session-loss translation, and the Search Inventory menu click.

## Preserved contract

No-driver characterization tests lock:

- readiness detection through the `documentLNISearch` field;
- caller-provided readiness timeouts;
- session-error classification on readiness failures;
- tab cleanup before pre-refresh alert handling;
- browser refresh followed by a 25-second document-ready wait;
- alert acceptance both before and after refresh;
- classification of alert and refresh errors without suppressing translated session
  loss;
- the initial 10-second readiness check;
- one Search Inventory menu fallback and a 15-second follow-up readiness check;
- short-circuiting that follow-up check when the menu click fails;
- `True` only when either readiness check succeeds, otherwise `False`.

The extracted helper does not enter an LNI, click the LNI search button, select a
result, or open/process a form. Those remain separate router responsibilities.
Structural coverage enforces that boundary. The full offline suite passed 148 tests
after extraction.

## Live validation not performed

No browser, authenticated staging system, production record, or external routing
action was used. A separately authorized smoke test should cover refresh success,
menu fallback, stale tabs, pending alerts, and lost-session propagation.

## Next gate

The LNI search retry loop and its call into this recovery boundary were subsequently
extracted into `lni_search_selenium.py`. Result selection/form opening and
duplicate-overlay UI remain separate, higher-risk phases.
