# Tab Lifecycle Selenium Extraction

Status: seventh helper slice implemented  
Scope: tab cleanup and focus restoration only

## New boundary

`core/router_modes/tab_lifecycle_selenium.py` owns the policies formerly implemented
by `CaseLawRouter._close_extra_tabs_and_focus_main()` and
`CaseLawRouter._cleanup_tabs()`.

Both router methods retain their signatures as thin compatibility entry points. The
module receives the router session-loss exception type explicitly, avoiding a
dependency back on the router class.

## Preserved policies

The two cleanup methods intentionally remain different.

Recovery cleanup:

- snapshots current handles;
- raises `RouterSessionLostError` when no window exists;
- prefers the tracked main handle, otherwise the first handle;
- closes every other handle in order;
- classifies close/focus failures through the router's session-error helper;
- focuses and retains the primary handle;
- clears only `_opened_tab`;
- returns `True` or `False`, while propagating session loss.

Local form cleanup:

- closes only the supplied opened tab when present;
- focuses the supplied main tab when present;
- otherwise focuses the first available handle;
- swallows driver errors;
- always clears `_opened_tab` and `_main_tab`;
- returns `None`.

No-driver tests passed against both implementations for tracked/stale main tabs,
multiple extras, no windows, nonfatal close errors, local fallback, and swallowed
switch failures. Structural tests keep search, alerts, routing, and status policy out
of this module. The full suite passed 119 tests after extraction.

## Live validation not performed

No browser, authenticated staging, or production record was used. Controlled
validation requires explicit authorization and safe multi-tab flows covering normal
completion, retry cleanup, stale tracked handles, failed closes, and session loss.

## Next gate

Browser-session loss classification and remaining-row status propagation were
subsequently extracted into the non-browser `session_loss_policy.py` boundary.
Reopen/modify recovery, duplicate-overlay UI, and search/open navigation remain
larger separately gated phases.
