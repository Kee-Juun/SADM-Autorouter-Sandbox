# Ready/Post-Click Selenium Extraction

Status: Phase 6A and fifteenth helper slice implemented  
Scope: Ready click, immediate alerts, overlays, and legacy outcomes only

## New boundary

`core/router_modes/ready_postclick_selenium.py` now owns the state machine formerly
implemented by `CaseLawRouter.click_ready_checkbox_and_check_overlay()`. The router
method retains its signature and descriptive contract as a thin compatibility entry
point. The legacy `is_counsel` argument remains accepted even though the state machine
does not use it.

## Preserved contract

Four return outcomes remain authoritative:

- `READY_NOT_CLICKABLE`: no Ready click succeeded;
- `ALERT_HANDLED`: an alert was accepted but no overlay followed;
- `True`: a fresh/duplicate/overlay path was handled;
- `False`: no overlay appeared, or post-click inspection failed and Save may proceed.

Fourteen no-driver tests lock:

- two Ready-click attempts;
- five-second clickable waits;
- alert handling and a one-second pause between click attempts;
- the 0.25-second pre-click pause;
- post-click alert draining;
- duplicate-alert delegation and overlay-clear waiting;
- direct Save clicking after the duplicate flow;
- route and workflow alerts treated as fresh-document outcomes;
- generic overlay detection and optional OK clicking;
- duplicate-overlay delegation after a generic overlay;
- `ALERT_HANDLED` when alerts end without an overlay;
- post-click inspection failures returning `False`;
- pre-click recovery failures returning `READY_NOT_CLICKABLE`.

The legacy direct Save click after duplicate handling remains inside this state
machine. Route selection and general save/retry behavior remain owned by
`routing_save_selenium.py`.

Structural coverage keeps routing selectors, status buffers, form filling, and
per-mode metadata outside this module. The full offline suite passed 213 tests after
extraction.

## Live validation not performed

No browser, authenticated staging system, production record, or external routing
action was used. A separately authorized staging test should cover every return
outcome, multiple queued alerts, duplicate overlays, optional OK controls, and
post-click driver failure.

## Next gate

Phase 6B is characterization only for `process_batch()` and `process_rows()`. Neither
method was decomposed during that phase, which is now complete. Phase 6C is limited to
pure batch-policy helpers while both methods remain the runtime implementations.
