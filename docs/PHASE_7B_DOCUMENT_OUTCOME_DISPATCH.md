# Phase 7B: Document-Row Outcome Dispatch

Status: complete  
Scope: selector-free dispatch around the five existing document-row wrappers

## Outcome

Phase 7B moves document handler selection, wrapper invocation, and five-slot metadata
normalization from `CaseLawRouter.process_batch()` into
`core/router_modes/document_row_outcome_dispatch.py`.

The dispatcher returns an immutable `DocumentRowOutcome`. It deliberately preserves:

- eager evaluation of ITC, IRSPLR, OHTAX0, and MNSUTB row predicates;
- precedence `mspb > itc > irsplr > ohtax0 > mnsutb > shared SMD/DAR`;
- exact invocation of one existing document-row compatibility wrapper;
- exactly one populated metadata slot for a continuing document row;
- all-empty metadata slots for shared fallback;
- unchanged propagation of predicate and wrapper exceptions;
- shared fallback for absent and unrecognized handlers.

The selector function and predicates are injected from the router. This retains the
existing patch points used by characterization tests and avoids importing Selenium,
configuration buffers, extractors, or the router into the dispatcher.

## Boundary retained by `process_batch()`

The router still owns:

- writing an early wrapper status and executing `continue`;
- shared SMD/DAR LNI search and its failure status;
- form opening and refresh/retry behavior;
- status-buffer precedence and finalization;
- counters, clocks, and throughput reporting;
- generic and session-loss exception handling;
- driver cleanup and progress emission.

No selector, wait, click, route, save, tab, alert, or form-fill implementation moved.
The dispatcher calls the same existing wrappers in the same outer `try` boundary.

## Verification

- direct dispatcher contracts: 8 tests passing;
- Phase 7A call-site characterization: 8 tests passing;
- combined mode/form boundary: 86 tests passing;
- full offline suite: 346 tests passing.

Measured after extraction:

| Item | Value |
| --- | ---: |
| `core/smducar_router.py` | 3,494 lines |
| `process_batch()` | 163 formatted lines |
| `process_rows()` | 59 lines |
| Router class methods | 156 |
| `core/router_modes/` Python modules | 40 |

Expected warning and error logs are deliberate failure-path tests.

## Safety and next gate

Only the Sandbox project was changed. No live browser, staging route, external
routing action, workbook write, or production-backup operation was performed.
MNSUTB Source Detail remains exactly `Table-(5-day spec source)`.

Phase 7B should end with an architecture checkpoint. The remaining shared search,
form open/retry, and driver-cleanup blocks directly control Selenium and must not be
moved under this approval.

The checkpoint is now complete. It recommends characterization-only Phase 8A for the
remaining form-transition call site. See `PHASE_7B_ARCHITECTURE_CHECKPOINT.md`.
