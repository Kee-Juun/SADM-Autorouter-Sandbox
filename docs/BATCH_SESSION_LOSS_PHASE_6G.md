# Phase 6G: Batch Router-Session-Loss Outcome

Status: fifth slice complete  
Scope: row-level router-session-loss logging, rerun marking, and error entry

## Outcome

The fifth Phase 6G slice extends
`core/router_modes/session_loss_policy.py` with
`handle_batch_session_loss()`.

The helper preserves this exact side-effect order:

1. log the row-level session-loss message;
2. call the existing remaining-row rerun marker;
3. append the existing error-report entry;
4. return an immutable `BatchSessionLossOutcome(stop_batch=True)`.

Failures during remaining-row marking still propagate before an error entry is
appended. Failures while appending still propagate after marking.

## Boundary retained by `process_batch()`

The `except RouterSessionLostError` clause invokes the helper and assigns its
`stop_batch` value. The router method still owns:

- the exception boundary itself;
- the `stop_batch` local variable;
- row progress in `finally`;
- forced `total / total` progress;
- the actual `break`;
- counters, duration, and batch return values;
- generic row exceptions;
- browser cleanup and all form routing.

No statement moved across the row's `finally` boundary.

## Verification

Three additional direct policy tests cover:

- exact log/mark/append order and payload;
- immutable stop outcome;
- marking failure before append;
- append failure after marking.

The existing process-batch session-loss test continues to lock remaining-row marking,
error status, progress sequence, and early stop. The focused session-loss/batch suite
passes 38 tests, and the full offline suite passes 311 tests.

No browser, staging route, external routing action, workbook write, or
production-backup operation was performed.

## Metrics

- `core/smducar_router.py`: 3,562 lines;
- `process_batch()`: 242 formatted lines;
- `process_rows()`: 59 lines;
- `core/router_modes/`: 36 Python modules.

## Next gate

Generic row-error recording is now complete in `batch_row_error.py`. Best-effort
driver window cleanup remains in `process_batch()`. See
`BATCH_ROW_ERROR_PHASE_6G.md`.
