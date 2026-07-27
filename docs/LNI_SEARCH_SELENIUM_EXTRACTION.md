# LNI Search Selenium Extraction

Status: eleventh helper slice implemented  
Scope: LNI field submission, Search click, availability check, and retries only

## New boundary

`core/router_modes/lni_search_selenium.py` now owns the loop formerly implemented by
`CaseLawRouter.search_lni()`. The router method retains its exact signature as a thin
compatibility entry point and supplies `RouterSessionLostError` explicitly.

The helper calls the existing result-availability method and the previously extracted
Search Inventory recovery method. It does not select a result row, open a form, or
enter Modify mode.

## Preserved contract

No-driver characterization tests lock:

- exactly three attempts;
- a session-validity precheck on every attempt;
- clearing the LNI field, waiting 0.5 seconds, entering the string value, and waiting
  another 0.5 seconds;
- clicking the Search button before checking result availability;
- immediate `True` when results become available;
- refresh recovery after the first and second no-result outcomes, but not after the
  third;
- continuing even when recovery cannot confirm readiness;
- a two-second pause after each recovery call;
- the exception text, or `search exception` for an empty message, in the recovery
  reason;
- translating classified session failures into `RouterSessionLostError` with the
  original exception chained;
- `False` after all attempts are exhausted.

The existing failed-precheck quirk is preserved: the locally raised session-loss
message is not recognized by the string classifier, so a false validity precheck is
retried and ultimately returns `False`. This phase does not convert that observation
into a behavior fix.

Structural coverage keeps result-row selectors, result clicking, form opening,
Modify-mode entry, and duplicate handling outside this module. The full offline suite
passed 158 tests after extraction.

## Live validation not performed

No browser, authenticated staging system, production record, or external routing
action was used. A separately authorized smoke test should cover first-attempt
success, delayed results, refresh fallback, exhausted searches, and lost sessions.

## Next gate

Result availability, selection, and popup/tab navigation were subsequently extracted
into `result_navigation_selenium.py`. Form-processing orchestration and
duplicate-overlay UI remain separate higher-risk Selenium phases requiring separate
approval.
