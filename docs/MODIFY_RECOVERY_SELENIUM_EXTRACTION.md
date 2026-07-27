# Modify Recovery Selenium Extraction

Status: ninth helper slice implemented  
Scope: Modify-mode entry, immediate alert classification, and local retries only

## New boundary

`core/router_modes/modify_recovery_selenium.py` now owns the Selenium routine formerly
implemented by `CaseLawRouter.attempt_open_modify()`. The router method retains its
full signature as a thin compatibility entry point, including the currently unused
`file_path` parameter.

The module receives `RouterSessionLostError` explicitly. It delegates session-error
classification and duplicate-popup handling back through existing router methods, so
it does not own duplicate-overlay DOM operations or Search Inventory navigation.

## Preserved contract

No-driver characterization tests lock:

- up to three Modify-button attempts by default;
- the 120-second clickable wait and five-second immediate-alert wait;
- success when no alert appears after the click;
- accepting `ready to process = [on]`, waiting five seconds, and retrying;
- accepting a duplicate-document alert and delegating popup handling;
- the DSAR duplicate sequence, including a two-second pause and optional second alert;
- translating classified driver failures into `RouterSessionLostError` with the
  original exception chained;
- two-second pauses after ordinary attempt failures, including the final failure;
- `ERROR: MODIFY FAILED` only when attempts are exhausted and a row index exists.

The tests also record an existing precheck quirk without correcting it: when
`check_session_validity()` returns false, the locally raised session-loss exception
does not contain one of the classifier's known message fragments. It is therefore
retried as an ordinary failure and ultimately returns `False`. Changing that behavior
requires a separate bug-fix decision.

Structural coverage keeps Search Inventory selectors and duplicate-overlay DOM
selectors outside this module. The full offline suite passed 137 tests after
extraction.

## Live validation not performed

No browser, authenticated staging system, production record, or external routing
action was used. A controlled smoke test would need explicit authorization and should
cover no-alert success, ready-to-process retry, duplicate sequences, and lost-session
behavior.

## Next gate

Search Inventory readiness and refresh/menu recovery were subsequently extracted into
`search_inventory_recovery_selenium.py`. LNI search retry orchestration,
duplicate-overlay UI, and the broader result/form-opening path remain higher-risk,
separately approved phases.
