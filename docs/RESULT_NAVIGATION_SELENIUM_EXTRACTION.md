# Result Navigation Selenium Extraction

Status: twelfth helper slice implemented  
Scope: result availability, selection, and popup/tab tracking only

## New boundary

`core/router_modes/result_navigation_selenium.py` now owns the behavior formerly
implemented by:

- `CaseLawRouter.check_result_available()`;
- `CaseLawRouter.handle_lni_search()`;
- `CaseLawRouter.click_matching_result()`;
- `CaseLawRouter.switch_to_popup_window()`.

All four router methods retain their signatures as thin compatibility entry points.
The helper calls the already-extracted LNI search boundary but does not process an IRT
form or enter Modify mode.

## Preserved contract

No-driver characterization tests lock:

- result availability through
  `td.searchColumn.ChangeMouseCursorToHand`;
- session-loss classification for availability failures;
- `handle_lni_search()` short-circuiting failed search or failed availability;
- result selection only after both checks succeed;
- the selection sequence: Ctrl+click, JavaScript middle-click, context-menu open in
  new tab, then direct-click popup fallback;
- five-second new-tab waits and the three-second context-menu option wait;
- tracking `_opened_tab` and `_main_tab` after a new tab opens;
- clearing `_opened_tab` and retaining the current main handle for direct-click
  fallback;
- popup switching to the last handle and returning the first handle;
- optional `show_error` reporting for selection or popup-switch failures.

Two existing limitations remain unchanged. `click_matching_result()` returns `None`
for both success and failure, so `handle_lni_search()` returns `True` after delegating
the click without confirming that a new page opened. Also, outer selection and popup
errors are reported and swallowed rather than passed through the session-loss
classifier. Changing either behavior requires a separate bug-fix phase.

Structural coverage keeps form filling, Modify entry, duplicate processing, and status
updates outside this module. The full offline suite passed 173 tests after extraction.

## Live validation not performed

No browser, authenticated staging system, production record, or external routing
action was used. A separately authorized smoke test should cover each new-tab method,
popup fallback, blocked popups, stale handles, and session loss.

## Next gate

`open_and_process_form()` orchestration was subsequently extracted into the
selector-free `form_opening_selenium.py`. Duplicate-overlay UI remains a separate
high-risk recovery boundary requiring independent approval.
