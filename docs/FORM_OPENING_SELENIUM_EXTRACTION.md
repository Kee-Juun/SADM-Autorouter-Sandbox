# Form Opening Selenium Extraction

Status: thirteenth helper slice implemented  
Scope: Modify/form delegation, cleanup, and fresh-start retries only

## New boundary

`core/router_modes/form_opening_selenium.py` now owns the orchestration formerly
implemented by `CaseLawRouter.open_and_process_form()`. The router method retains its
complete signature as a thin compatibility entry point.

The module is selector-free and contains no Selenium imports. It coordinates existing
boundaries for Modify entry, form filling, tab cleanup, Search Inventory recovery, LNI
search, and result navigation.

## Preserved contract

Characterization tests lock:

- capturing the tracked main/form handles, with the current driver handle as the main
  fallback;
- calling `attempt_open_modify()` with the row index;
- forwarding every mode and metadata argument to `fill_irt_form()` with
  `skip_ready_check=True`;
- submitting and buffering only an exact `DONE` result;
- cleaning the captured tabs for every normal returned form status;
- immediate cleanup after a failed Modify attempt;
- trimming the row LNI before refresh and re-search;
- exact refresh and re-search failure statuses;
- recursive retry with every argument preserved and the retry count incremented;
- stopping after the third failed Modify attempt with
  `ERROR: MODIFY BUTTON NOT FOUND AFTER 3 ATTEMPTS`.

An existing limitation remains unchanged: exceptions from form filling or submission
propagate before cleanup because cleanup is not protected by a `finally` block. A
cleanup guarantee would be a behavioral bug fix and needs a separate decision.

Structural coverage keeps selectors, waits, duplicate handling, and direct browser
actions outside this module. The full offline suite passed 183 tests after extraction.

## Live validation not performed

No browser, authenticated staging system, production record, or external routing
action was used. A separately authorized smoke test should cover normal completion,
non-DONE returns, all three fresh-start attempts, refresh/re-search failures, and tab
cleanup.

## Next gate

Duplicate-overlay UI was subsequently characterized and extracted into
`duplicate_overlay_selenium.py`, including its archive/process policy, Continue
fallback, overlay-clear checks, and diagnostics.
