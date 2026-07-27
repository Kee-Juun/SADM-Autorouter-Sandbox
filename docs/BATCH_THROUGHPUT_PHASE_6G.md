# Phase 6G: Batch Throughput Summary

Status: fourth slice complete  
Scope: post-loop throughput calculation and legacy summary logging

## Outcome

The fourth Phase 6G slice moves the post-loop calculation and log formatting from
`CaseLawRouter.process_batch()` into
`core/router_modes/batch_throughput.py`.

`process_batch()` retains the `processed_count > 0` gate and supplies:

- processed count;
- accumulated per-LNI duration;
- batch start time;
- batch label;
- its current `time.time` callable.

Injecting the clock preserves existing patching and call order without making the
helper depend on the router or the `time` module.

## Preserved ordering

The helper performs operations in the legacy order:

1. calculate average duration;
2. calculate the integer hourly estimate;
3. read the final clock;
4. truncate elapsed minutes and seconds;
5. emit the exact summary string.

A positive processed count with zero total duration therefore still raises
`ZeroDivisionError` before the final clock is read. Clock failures still propagate
before logging.

## Boundary retained by `process_batch()`

The router method still owns:

- the positive-count gate;
- batch and LNI start/end clock placement;
- all counters and duration accumulation;
- loop, `continue`, `finally`, stop, and `break` behavior;
- progress callbacks;
- status, metadata, and error buffers;
- row and session-loss exceptions;
- every browser and form-routing operation;
- the returned `(processed_count, total_duration)` tuple.

## Verification

Five no-driver tests in `tests/test_batch_throughput_summary.py` cover:

- the exact legacy summary;
- average, hourly-rate, minute, and second calculations;
- integer elapsed-time truncation;
- zero-duration division before the final clock;
- final-clock error propagation;
- module isolation from runtime state and Selenium.

The existing batch success test also asserts the exact integrated summary line. The
focused throughput/batch suite passes 17 tests, and the full offline suite passes 308
tests.

No browser, staging route, external routing action, workbook write, or
production-backup operation was performed.

## Metrics

- `core/smducar_router.py`: 3,562 lines;
- `process_batch()`: 243 formatted lines;
- `process_rows()`: 59 lines;
- `core/router_modes/`: 36 Python modules.

## Next gate

Router-session-loss row handling is now complete in `session_loss_policy.py`.
`stop_batch`, row `finally`, forced progress, and the actual `break` remain in
`process_batch()`. See `BATCH_SESSION_LOSS_PHASE_6G.md`.
