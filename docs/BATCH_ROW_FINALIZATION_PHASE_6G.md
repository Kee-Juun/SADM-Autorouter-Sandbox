# Phase 6G: Post-Form Batch-Row Finalization

Status: eighth slice complete  
Scope: form-status replacement, LNI duration, increments, and timing log

## Outcome

The eighth Phase 6G slice moves post-form row finalization into
`core/router_modes/batch_row_finalization.py`.

`finalize_batch_row()`:

- applies the existing form-status replacement policy;
- writes a replacement status only when the policy returns one;
- reads the injected end clock after status handling;
- returns an immutable `BatchRowFinalizationOutcome` containing duration, a
  processed-count increment, and the replacement status.

`log_batch_row_duration()` emits the exact legacy per-LNI timing message.

## Preserved order

Runtime order remains:

1. refresh retry completes in `process_batch()`;
2. status replacement and optional buffer write;
3. LNI end-clock read;
4. router adds the duration;
5. router increments processed count;
6. extracted per-LNI timing log.

Status-write failures still occur before the clock. Clock failures still occur after
any replacement but before counters or logging.

## Boundary retained by `process_batch()`

The router method still owns:

- form opening and returned status;
- refresh/retry decisions and execution;
- the local duration and count accumulators;
- applying immutable increments;
- the relative placement of the timing log;
- exception handling, progress, loop control, and batch return values;
- every Selenium and browser operation.

## Verification

Seven no-driver tests cover:

- status replacement and exact duration;
- completed-form status preservation;
- existing nonprocessing-status preservation;
- immutable increments;
- status-write failure before clock;
- clock failure after replacement;
- exact legacy per-LNI log;
- module isolation from Selenium, configuration, buffers, router, and `time`.

The integrated batch success test asserts both the exact per-LNI timing line and the
exact batch throughput line. The focused finalization/batch suite passes 20 tests,
and the full offline suite passes 330 tests.

No browser, staging route, external routing action, workbook write, or
production-backup operation was performed.

## Metrics

- `core/smducar_router.py`: 3,554 lines;
- `process_batch()`: 226 formatted lines;
- `process_rows()`: 59 lines;
- `core/router_modes/`: 39 Python modules.

## Next gate

The Phase 6G architecture checkpoint is complete and recommends stopping code
movement here. See `PHASE_6G_ARCHITECTURE_CHECKPOINT.md`. Further work should begin
with a characterization-only Phase 7A.
