# Phase 6G: Generic Batch-Row Error Recording

Status: sixth slice complete  
Scope: generic row-error logging, metadata recording, and error buffers

## Outcome

The sixth Phase 6G slice moves the non-browser portion of the generic
`process_batch()` exception branch into
`core/router_modes/batch_row_error.py`.

`record_batch_row_error()` receives all mutable buffers and row predicates
explicitly. It preserves:

- the row-number error log;
- precedence `mspb > itc > irsplr > ohtax0 > mnsutb`;
- use of the shared MSPB metadata buffer for the existing metadata-status lookup;
- `Extracted` only when the buffered value is exactly `Extracted`;
- the selected router metadata recorder and its arguments;
- row status `ERROR`;
- the legacy error-report entry;
- propagation order when recording or buffer writes fail.

It returns an immutable `BatchRowErrorOutcome` describing the selected metadata mode
and status. The runtime currently does not need that result.

## Boundary retained by `process_batch()`

The router still owns:

- the generic `except Exception` clause;
- the helper invocation and injected predicates/buffers;
- best-effort `driver.close()`;
- switching back to the first window;
- swallowing cleanup failures;
- the row's `finally` progress;
- all loop control, counters, timing, and form routing.

If error recording raises, driver cleanup remains unexecuted and the row's `finally`
still runs, matching the previous statement order.

## Verification

Five isolated tests cover:

- every document-mode recorder and legacy precedence;
- exact shared metadata-status lookup;
- generic non-document status/error recording;
- immutable outcome;
- recorder failure before buffer writes;
- error-entry failure after status update;
- isolation from Selenium, configuration, buffers, and extractor imports.

An additional process-batch integration test proves that recording failure propagates
before driver cleanup while `finally` progress still occurs. The focused
row-error/batch suite passes 18 tests, and the full offline suite passes 317 tests.

No browser, staging route, external routing action, workbook write, or
production-backup operation was performed.

## Metrics

- `core/smducar_router.py`: 3,550 lines;
- `process_batch()`: 227 formatted lines;
- `process_rows()`: 59 lines;
- `core/router_modes/`: 37 Python modules.

## Next gate

Row preflight is now complete in `batch_row_preflight.py`. The router retains
`continue`, LNI timing, mode dispatch, and all browser behavior. See
`BATCH_ROW_PREFLIGHT_PHASE_6G.md`.
