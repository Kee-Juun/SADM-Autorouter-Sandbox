# Phase 6G: Batch Progress Emission

Status: third slice complete  
Scope: repeated `process_batch()` progress-callback eligibility and invocation

## Outcome

The outer-loop review identified progress emission as the smallest safe
non-Selenium seam. `core/router_modes/batch_policy.py` now provides
`emit_batch_progress()`.

`process_batch()` uses the helper at the same three lifecycle points:

1. `0 / total` before iteration;
2. `processed_rows / total` in every row's `finally`;
3. forced `total / total` after router-session loss.

The helper preserves the exact supported batch labels and callback argument order.
It returns whether a callback was emitted, although the current runtime does not use
that return value.

## Boundary retained by `process_batch()`

The router method still owns:

- alert cleanup and all loop counters;
- dataframe iteration and row lookup;
- completed and invalid-row short circuits;
- status and metadata buffers;
- mode-handler selection and document-row wrappers;
- all form opening, retry, and Selenium behavior;
- processed-count and duration semantics;
- generic and router-session-loss exception boundaries;
- deciding when each progress event occurs;
- stop/break control;
- throughput calculation and summary logging.

No callback was moved across a `try`, `except`, `finally`, or `break` boundary.

## Verification

Three pure policy tests cover:

- exact supported callback invocation;
- unsupported-label suppression;
- missing-callback suppression.

The existing direct batch suite continues to lock start, per-row, unsupported-label,
and session-loss completion sequences. The focused batch suite passes 24 tests and
the full offline suite passes 303 tests.

No browser, staging route, external routing action, workbook write, or
production-backup operation was performed.

## Metrics

- `core/smducar_router.py`: 3,559 lines;
- `process_batch()`: 243 formatted lines;
- `process_rows()`: 59 lines;
- `core/router_modes/`: 35 Python modules.

The formatted line count increased because three compact conditionals became
readable multi-line helper calls. Line count is not the success criterion; centralized
and directly tested callback policy is.

## Next gate

The throughput-summary seam is now complete in `batch_throughput.py`, including its
clock ordering and zero-duration behavior. See `BATCH_THROUGHPUT_PHASE_6G.md`.
