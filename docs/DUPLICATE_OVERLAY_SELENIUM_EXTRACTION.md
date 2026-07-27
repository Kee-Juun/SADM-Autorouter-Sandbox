# Duplicate Overlay Selenium Extraction

Status: fourteenth helper slice implemented  
Scope: duplicate policy, popup entry, overlay controls, clearing, and diagnostics

## New boundary

`core/router_modes/duplicate_overlay_selenium.py` now owns the duplicate-specific
behavior formerly implemented by twelve `CaseLawRouter` methods:

- route-sensitive archive/process policy;
- duplicate alert and popup entry;
- three-attempt overlay recovery;
- Process as New and Archive as Duplicate selection;
- archive-option and Continue-button discovery;
- native and JavaScript click fallbacks;
- overlay-clear verification;
- visible-dialog detection and diagnostics.

Every router method retains its original signature as a thin compatibility entry
point. Existing alert acceptance remains in `alert_recovery_selenium.py`; routing and
save behavior remain in `routing_save_selenium.py`.

## Preserved contract

No-driver characterization tests lock:

- explicit `archive_as_duplicate` overriding `_archive_duplicate_mode`;
- Process as New as the default policy;
- alert acceptance before selection, between selection and Continue, and after
  Continue;
- three attempts, one-second pauses after the first two ordinary failures, and final
  diagnostics;
- immediate alert acceptance and retry for `UnexpectedAlertPresentException`;
- optional duplicate-alert acceptance before overlay handling;
- early return for a nonduplicate alert;
- native radio clicking with JavaScript fallback;
- dynamic archive-option discovery by IDs, radio attributes, labels, and visible text;
- Continue discovery with OK and first-visible-button fallbacks;
- waiting until duplicate dialogs, overlays, and visible-dialog radios are gone.

The helper still swallows top-level popup-handling failures after attempting to accept
one fallback alert. That is existing recovery behavior and was not changed.

Structural coverage keeps route selection, Save, status buffers, and per-mode
metadata outside the module. The full offline suite passed 199 tests after extraction.

## Live validation not performed

No browser, authenticated staging system, duplicate record, production record, or
external routing action was used. A separately authorized staging test should verify
both policies, unexpected-alert retries, alternate Continue controls, JavaScript
fallbacks, and overlay disappearance.

## Next gate

The architecture and test-coverage review was subsequently completed. It identified
Ready/post-click characterization as Phase 6A and batch characterization as Phase 6B.
Phase 6A is now implemented in `ready_postclick_selenium.py`; `process_batch()` and
`process_rows()` remain intentionally unchanged.
