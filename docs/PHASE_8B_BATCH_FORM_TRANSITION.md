# Phase 8B: Batch Form-Transition Wrapper

Status: complete  
Scope: selector-free shared-search, form-open, and refresh-retry transition

## Outcome

Phase 8B moves the characterized browser-adjacent transition from
`CaseLawRouter.process_batch()` into
`core/router_modes/batch_form_transition.py`.

The wrapper returns an immutable `BatchFormTransitionOutcome` containing:

- `continue_to_finalization`;
- the final `form_status`;
- an optional early `row_status`.

It deliberately preserves:

- shared LNI search only when no document handler owns the row;
- shared-search failure status `ERROR: LNI NOT FOUND`;
- exact form-open arguments, flags, and five metadata slots;
- retry eligibility evaluation after the initial form return;
- exact refresh/retry argument forwarding;
- replacement of initial status by retry status;
- unchanged propagation of ordinary and session-loss exceptions.

## Boundary retained by `process_batch()`

The router still owns:

- applying the early row status to `status_updates_buffer`;
- the early `continue`;
- post-transition finalization and status-buffer precedence;
- duration and processed-count mutation;
- session-loss and generic exception selection;
- generic error recording and direct driver cleanup;
- per-row progress, stop/break control, throughput, and return values.

No selector, wait, click, form-fill, routing, save, alert, or tab implementation
moved. The wrapper calls the same existing router compatibility methods inside the
same outer `try`.

## Direct contracts

`tests/test_batch_form_transition.py` adds nine direct tests covering:

- shared search/open order and exact arguments;
- shared-search failure outcome;
- document-path search suppression and metadata forwarding;
- non-recoverable retry bypass;
- exact recoverable retry arguments;
- retry-result replacement;
- unchanged propagation from all four transition calls;
- immutable outcomes;
- module isolation from Selenium, router/config imports, buffers, and direct driver
  access.

The Phase 8A call-site suite remains in place and verifies application of the wrapper
outcome by the real outer loop.

## Verification

- direct Phase 8B suite: 9 tests passing;
- Phase 8A call-site suite: 8 tests passing;
- combined mode/form boundary: 103 tests passing;
- full offline suite: 363 tests passing.

Measured after extraction:

| Item | Value |
| --- | ---: |
| `core/smducar_router.py` | 3,480 lines |
| `process_batch()` | 146 formatted lines |
| `process_rows()` | 59 lines |
| Router class methods | 156 |
| `core/router_modes/` Python modules | 41 |
| `batch_form_transition.py` | 69 lines |

Expected warning and error logs are deliberate failure-path tests.

## Safety and next gate

Only the Sandbox project was changed. No live browser, staging route, external
routing action, workbook write, or production-backup operation was performed.
MNSUTB Source Detail remains exactly `Table-(5-day spec source)`.

Because this wrapper invokes browser-adjacent compatibility methods, the absence of a
staging smoke test is recorded explicitly. The next step should be an architecture
checkpoint. Generic driver cleanup remains direct Selenium behavior and is not
authorized for extraction by Phase 8B.

The checkpoint is now complete. It recommends ending further batch-code movement
and proceeding with a documentation-only developer mode-integration guide. See
`PHASE_8B_ARCHITECTURE_CHECKPOINT.md`.
