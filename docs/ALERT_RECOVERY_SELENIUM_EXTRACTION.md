# Alert Recovery Selenium Extraction

Status: sixth helper slice implemented  
Scope: pending-alert acceptance and duplicate-alert classification only

## New boundary

`core/router_modes/alert_recovery_selenium.py` owns the sequences formerly implemented
by `CaseLawRouter.accept_pending_alerts()` and `CaseLawRouter.handle_any_alert()`.

Both router methods retain their exact signatures as thin compatibility entry points.
All callers continue using the router. When a duplicate alert is classified, the
extracted helper delegates to the unchanged `CaseLawRouter.handle_duplicate_overlay()`
method.

Duplicate-overlay selectors, radio choices, Continue controls, clearing waits, and
diagnostics remain in the router.

## Preserved contract

No-driver tests passed against both implementations and lock:

- no alert returning `(False, False)`;
- exact initial timeout on the first wait;
- follow-up timeout after the first accepted alert;
- alert text trimming and acceptance order;
- a 0.25-second delay after each accepted alert;
- case-insensitive `duplicate document` classification;
- the `max_alerts` bound;
- timeout ending the loop normally;
- unexpected wait errors preserving accumulated state and ending the loop;
- `handle_any_alert()` returning the handled-alert Boolean;
- duplicate classification invoking the overlay handler with the exact
  `archive_as_duplicate` value;
- no overlay call for nonduplicate alerts;
- thin router wrappers and no duplicate-overlay UI implementation in the module.

The full suite passed 110 tests after extraction.

## Live validation not performed

No browser, authenticated staging, or production record was used. Controlled
validation requires explicit authorization and safe flows with no alert, ordinary
alerts, duplicate alerts, multiple sequential alerts, and overlay completion.

## Next gate

Tab cleanup and focus restoration were subsequently characterized and extracted.
Remaining recovery coupling is divided among:

- duplicate-overlay UI and diagnostics;
- reopen/modify recovery;
- browser-session loss classification and remaining-row statuses;
- search/open navigation.

Each requires a separately characterized boundary. Session-loss classification and
status propagation is the narrowest candidate for the next phase.
