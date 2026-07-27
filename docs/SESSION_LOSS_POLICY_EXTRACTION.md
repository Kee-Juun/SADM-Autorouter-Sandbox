# Session-Loss Policy Extraction

Status: eighth helper slice implemented  
Scope: browser-session error classification and remaining-row status policy only

## New boundary

`core/router_modes/session_loss_policy.py` now owns three policies formerly
implemented directly by `CaseLawRouter`:

- case-insensitive classification of known lost-session error messages;
- translation of a classified error into `RouterSessionLostError`;
- marking the current and remaining assigned rows as interrupted.

The original router methods retain their signatures as thin compatibility entry
points. `RouterSessionLostError` remains defined and exported by
`core/smducar_router.py`; the wrapper supplies that exception type to the policy
module explicitly, avoiding a dependency back on the router class.

## Preserved behavior

Classification recognizes the same six message fragments:

- `invalid session id`
- `chrome not reachable`
- `disconnected`
- `not connected to devtools`
- `target window already closed`
- `no such window`

Exception translation preserves the context-bearing message and chains the original
exception as its cause. Ordinary errors are not translated.

Remaining-row propagation:

- starts at the current full-dataframe index, inclusively;
- does nothing when that index is absent;
- reads a buffered status before the dataframe status;
- preserves only `DONE` and `ALREADY PROCESSED`, after trimming and uppercasing;
- writes `NEEDS RERUN - INTERRUPTED` for every other remaining row;
- retains the existing router-session-loss log message.

The extracted module contains no Selenium imports or driver operations. Characterization
and structural tests cover the policies and the thin router wrappers. The full offline
suite passed 127 tests after extraction.

## Live validation not performed

No browser, authenticated staging system, production record, or external routing
action was used. Live session-loss behavior remains suitable for a separately
authorized controlled smoke test.

## Next gate

Modify-mode entry was subsequently extracted into
`modify_recovery_selenium.py`. Search Inventory refresh/retry, duplicate-overlay UI,
and search/open navigation remain separately approved Selenium phases.
