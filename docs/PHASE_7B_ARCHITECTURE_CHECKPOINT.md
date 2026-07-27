# Phase 7B Architecture Checkpoint

Status: complete; documentation only  
Scope: remaining `CaseLawRouter.process_batch()` orchestration after Phase 7B

## Decision

Phase 7B is complete. No production code moved during this checkpoint.

The remaining 163-line `process_batch()` is a readable outer orchestration shell.
Mode selection and mode-specific document-row outcomes are now behind an immutable
dispatcher. The largest remaining contiguous behavior is the browser-controlled
transition from optional shared LNI search through form opening and refresh retry.
That transition must not move under the Phase 7B authorization.

## Current measured structure

| Item | Value |
| --- | ---: |
| `core/smducar_router.py` | 3,494 lines |
| `process_batch()` | 163 formatted lines |
| `process_rows()` | 59 lines |
| Router class methods | 156 |
| `core/router_modes/` Python modules | 40 |
| Full offline suite | 346 tests |

Line count is a navigation aid, not an extraction target.

## Remaining `process_batch()` map

Line numbers describe the Phase 7B checkpoint source and may shift later.

| Lines | Responsibility | Classification |
| --- | --- | --- |
| 2172-2184 | alert cleanup, counters, clocks, initial progress | Batch lifecycle |
| 2186-2200 | row lookup, preflight, `continue`, row clock | Outer-loop control |
| 2202-2221 | document dispatcher call and early outcome application | Extracted boundary application |
| 2223-2226 | shared SMD/DAR LNI search and failure status | Direct Selenium transition |
| 2228-2259 | form opening, retry decision, refresh/retry invocation | Browser-controlled transition |
| 2261-2272 | status finalization, counters, duration log | Extracted boundary application |
| 2276-2302 | session-loss and generic-error paths, driver cleanup | Mixed policy and direct Selenium |
| 2304-2317 | forced row progress and stop/break control | Outer-loop lifecycle |
| 2319-2333 | throughput summary and return | Extracted boundary application |

## Boundaries that should remain in the router

The following responsibilities express the outer loop and are already concise:

- dataframe iteration and row lookup;
- `continue`, `break`, and processed-row progress placement;
- counter accumulation and batch return values;
- the outer exception and `finally` structure;
- applying immutable outcomes to shared buffers.

Moving these would hide control flow without creating a reusable mode boundary.

## Separately gated browser boundaries

### Shared search and form transition

The shared path calls `handle_lni_search()` only when no document handler owns the
row. Every continuing path then calls `open_and_process_form()` and may call
`_refresh_and_retry_current_row()`. Although the call site contains no selectors,
these calls directly control browser navigation, form state, refresh, and retry
ordering.

### Generic driver cleanup

After generic error recording, the router closes the active window and focuses the
first remaining handle on a best-effort basis. This is a small block but directly
mutates browser state. Extracting it alone would add indirection without improving
mode modularity.

## Existing evidence

The current offline contracts already cover:

- shared search only when no document handler exists;
- shared-search failure status and early skip;
- exact five-slot document metadata forwarding;
- recoverable form status refresh/retry and finalization;
- generic error recording before driver cleanup;
- failure of error recording before cleanup;
- session-loss stop and forced final progress;
- form-opening recursion, argument forwarding, modify failure, re-search failure,
  and tracked-tab cleanup.

The 86-test mode/form boundary and all 346 offline tests pass.

## Recommended Phase 8A

If further modularization is desired, Phase 8A should be characterization only for
the remaining batch form-transition call site. A dedicated no-driver suite should
lock:

- exact shared-search success/failure ordering;
- document-handler suppression of shared search;
- exact form-open arguments for shared and document paths;
- non-recoverable status bypassing refresh retry;
- recoverable status invoking one refresh/retry with unchanged metadata and flags;
- retry-result finalization;
- search, form-open, retry-decision, and retry-call failures entering the current
  generic-error/cleanup/`finally` sequence.

Do not move code in Phase 8A. A later Phase 8B extraction would be selector-free but
browser-adjacent and therefore requires explicit approval and a separate decision on
staging smoke validation.

Phase 8A is now complete with eight dedicated no-driver tests and no production
source change. The optional Phase 8B transition wrapper remains separately gated.
See `PHASE_8A_BATCH_FORM_TRANSITION_CHARACTERIZATION.md`.

## Safety record

Only the Sandbox project was inspected and documented. No live browser, staging
route, external routing action, workbook write, Selenium selector, or production
backup was touched. MNSUTB Source Detail remains exactly
`Table-(5-day spec source)`.
