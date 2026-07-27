# Phase 6G: Batch-Row Preflight

Status: seventh slice complete  
Scope: completed-status, validation, and `PROCESSING` transition

## Outcome

The seventh Phase 6G slice moves row preflight into
`core/router_modes/batch_row_preflight.py`.

`prepare_batch_row()` returns an immutable `BatchRowPreflightOutcome` with one of:

- `completed`: preserve the normalized completed status and skip validation;
- `invalid`: validation returned a falsey LNI;
- `process`: mark the row `PROCESSING` and return the exact validated LNI.

The existing status buffer and `mark_row_processing` function are supplied
explicitly. The helper imports neither configuration nor rerun-status state.

## Preserved order

The helper preserves:

1. completed-status normalization;
2. completed-row log;
3. completed-status buffer write;
4. LNI validation only for noncompleted rows;
5. falsey-LNI decision;
6. `PROCESSING` transition only for valid rows.

Validation, status-buffer, and processing-mark failures still propagate into the
existing generic row exception branch.

## Boundary retained by `process_batch()`

The router method still owns:

- dataframe iteration and row lookup;
- the `try`/exception boundary;
- both `continue` decisions;
- assigning the returned LNI;
- the LNI start clock after successful preflight;
- mode detection and document-row dispatch;
- form opening and retry;
- timing completion, counters, progress, and all browser behavior.

## Verification

Six no-driver tests cover:

- completed status, logging, and validation suppression;
- invalid-LNI behavior;
- exact valid-LNI return and processing mark;
- immutable outcome;
- validation failure before marking;
- marking failure after validation;
- isolation from Selenium, pandas, router/config imports, and shared buffers.

Existing direct batch tests continue to lock completed-row and invalid-row progress,
valid-row timing/counting, and generic error handling. The focused preflight/batch
suite passes 24 tests, and the full offline suite passes 323 tests.

No browser, staging route, external routing action, workbook write, or
production-backup operation was performed.

## Metrics

- `core/smducar_router.py`: 3,552 lines;
- `process_batch()`: 227 formatted lines;
- `process_rows()`: 59 lines;
- `core/router_modes/`: 38 Python modules.

## Next gate

Post-form row finalization is now complete in `batch_row_finalization.py`. Form
opening, refresh retry, counter mutation, loop control, and Selenium remain in
`process_batch()`. See `BATCH_ROW_FINALIZATION_PHASE_6G.md`.
