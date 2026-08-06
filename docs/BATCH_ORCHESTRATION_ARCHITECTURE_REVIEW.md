# Batch Orchestration Architecture and Coverage Review

Status: Phase 8B architecture checkpoint complete  
Scope: `CaseLawRouter.process_batch()` and `CaseLawRouter.process_rows()`  
Baseline before Phase 6C: 232 offline tests passing

Documentation entry point: [README.md](README.md)  
Current closeout: [MODULARIZATION_CLOSEOUT.md](MODULARIZATION_CLOSEOUT.md)

## Outcome

The reusable mode, form, navigation, save, alert, tab, session-loss, and duplicate
boundaries are substantially clearer. The remaining `process_batch()` outer loop is
not ready for behavior-preserving extraction.

`process_batch()` and the remaining `process_rows()` shell coordinate
behavior-sensitive contracts.
Phase 6B added direct characterization before any batch movement, Phase 6C
centralized only pure decisions, Phase 6D moved the MSPB row sequence, and Phase 6E
has moved the OHTAX0, MNSUTB, ITC, and IRSPLR sequences behind outcome-returning
compatibility wrappers.
Phase 6F then extracted document-only run dispatch, and the first Phase 6G slice
extracted shared SMD/DAR counsel/defer/window-cleanup/main orchestration.

An additional prerequisite emerged during review:
`click_ready_checkbox_and_check_overlay()` was a shared 98-line Selenium state machine
used by all seven active modes with no direct characterization suite. Phase 6A has now
characterized and extracted it into `ready_postclick_selenium.py`.

## Current snapshot

| Item | Current value |
| --- | ---: |
| `core/smducar_router.py` | 3,480 lines |
| `process_batch()` | 146 formatted lines |
| `process_rows()` | 59 lines |
| `click_ready_checkbox_and_check_overlay()` | 98 lines |
| Single-return router compatibility methods | 40 |
| Other router methods | 116 |
| `core/router_modes/` Python modules | 41 |
| Offline test methods after 2026-07-28 sync | 373 |
| Direct `process_batch()` tests | 13 |
| Direct `process_rows()` tests | 7 |
| Direct Ready/post-click state-machine tests | 14 |

The remaining methods do not all need extraction. Many are small compatibility
utilities or mode-specific browser/PDF helpers. Line count is a navigation aid, not a
refactoring target by itself.

## `process_batch()` responsibilities

The method currently owns:

1. initial alert cleanup and when to emit `0 / total` progress;
2. iteration over original dataframe indices;
3. row-preflight delegation and skip decisions;
4. LNI assignment and timing start after successful preflight;
5. row-aware mode-handler precedence;
6. per-mode metadata attempt, search, extraction, fallback, and recording;
7. result selection and form-opening delegation;
8. one recoverable-form refresh/retry;
9. post-form finalization delegation and counter mutation;
10. duration accumulation and when to emit row/batch timing logs;
11. router-session-loss outcome delegation and stop/break control;
12. generic error-recording delegation and local browser cleanup;
13. when to emit per-row progress in `finally`;
14. when to force final progress and stop after session loss.

### Behavior-sensitive asymmetries

- MSPB mode takes precedence over row predicates.
- ITC selection is row-aware; `process_batch()` has no `itc_mode` parameter.
- IRSPLR missing metadata creates unreadable-PDF fallback metadata and still opens the
  form.
- MSPB, ITC, OHTAX0, and MNSUTB missing metadata skip the row with mode-specific
  statuses.
- `processed_rows` advances for every loop iteration through `finally`, while
  `processed_count` advances only after form processing reaches the timing block.
- Completed and invalid rows therefore affect progress but not throughput counts.
- A router-session loss marks the current and remaining rows, emits an error-log
  record, forces progress to `total / total`, and stops the batch.
- A generic exception writes `ERROR`, attempts mode-specific metadata error recording,
  and best-effort closes the active window.
- A returned form status replaces buffered `PROCESSING` only when it is noncompleted.

These details must remain explicit until a separate behavior-change phase.

## `process_rows()` responsibilities

The method currently owns:

1. storing `full_df` on the router;
2. initial counsel/main filtering;
3. document-only dispatch and its early return;
4. shared SMD/DAR dispatch;
5. shared-run finalization delegation;
6. normal-outcome exception classification and logging;
7. broad exception conversion to two empty dataframes.

The effective branch order is:

```text
mspb > itc > irsplr > ohtax0 > mnsutb > shared SMD/DAR
```

Document-only modes return immediately after their single batch. SMD/DAR alone run
the counsel/defer/cleanup/main sequence.

## Current direct coverage

| Boundary | Direct coverage | Review assessment |
| --- | --- | --- |
| Registry, compatibility, run planning | Dedicated unit tests | Strong |
| Specialized handler selection/delegation | Dedicated unit tests | Strong |
| Extracted mode/form/navigation/recovery helpers | Characterization suites | Strong offline contract |
| `process_batch()` specialized modes | 13 total direct batch tests | Phase 6B complete |
| Shared SMD/DAR batch branch | Direct happy-path test | Characterized |
| Batch skip/error/session-loss/progress behavior | Direct branch tests | Characterized |
| `process_rows()` mode dispatch | 7 direct tests | Phase 6B complete |
| Counsel/main sequencing and deferral | Direct router tests | Characterized |
| Ready/post-click state machine | 14 direct tests | Phase 6A complete |
| Live browser behavior | Not performed | Explicit validation gap |

## Required characterization before batch movement

### Ready/post-click state machine

Lock:

- two Ready-click attempts and their exact waits;
- alert handling between attempts;
- `READY_NOT_CLICKABLE`, `ALERT_HANDLED`, `True`, and `False` outcomes;
- duplicate-alert handling and overlay-clear flow;
- route/workflow alerts treated as fresh documents;
- generic overlay plus optional OK handling;
- Save click after duplicate handling;
- post-click inspection failures proceeding to Save;
- pre-click failures treated as already processed.

### `process_batch()`

Lock:

- initial and per-row progress for supported and unsupported batch labels;
- completed-row and invalid-LNI short circuits;
- success, search failure, and metadata failure for each specialized mode;
- IRSPLR unreadable-PDF fallback;
- shared SMD/DAR search path;
- recoverable form-status retry and final status precedence;
- exact metadata arguments and call order;
- generic error metadata/status/log behavior by mode;
- router-session-loss marking, progress completion, and early stop;
- processed-count and duration semantics.

### `process_rows()`

Lock:

- exact single-batch arguments, status callbacks, returns, and early exits for MSPB,
  ITC, IRSPLR, OHTAX0, and MNSUTB;
- legacy contradictory-flag precedence;
- SMD and DAR counsel/main batch order;
- counsel-dependent main deferral;
- between-batch window cleanup;
- success state;
- error-report creation behind patched filesystem/Excel boundaries;
- broad-exception fallback to two empty dataframes.

## Recommended phased plan

### Phase 6A: Ready/post-click characterization and extraction

Implementation status: completed in `ready_postclick_selenium.py`.

Add no-driver tests first, then move only
`click_ready_checkbox_and_check_overlay()` behind its existing router signature.
Keep route/save decisions in `routing_save_selenium.py` and duplicate UI in
`duplicate_overlay_selenium.py`.

Exit gate: every return value and alert/overlay branch matches the current method.

### Phase 6B: Batch characterization only

Implementation status: completed in
`test_process_batch_characterization.py` and
`test_process_rows_characterization.py`.

Add the `process_batch()` and `process_rows()` tests listed above. Do not move code in
this phase.

Exit gate: all mode branches, progress, status, exception, and callback contracts are
executable without a browser.

### Phase 6C: Pure batch policy helpers

Implementation status: completed in `batch_policy.py` and adopted by both batch
methods without moving their runtime control flow.

The data-only helpers cover:

- supported progress labels;
- form-status finalization;
- completed-row recognition;
- mode-specific missing-metadata outcomes;
- document-only batch descriptions.

These helpers must not import Selenium, pandas, the router class, or global buffers.

Exit gate: policy tests prove identical decisions for every characterized input.

### Phase 6D: One document-row wrapper

Implementation status: completed for MSPB in `mspb_batch_row.py`.

The wrapper returns an immutable outcome while the outer loop retains global buffer
writes, loop control, exception boundaries, progress, and timing.

Exit gate: recorded method calls, metadata records, status updates, and return values
match the baseline.

### Phase 6E: Remaining document-row wrappers

Proceed one mode at a time:

```text
MSPB -> OHTAX0 -> MNSUTB -> ITC -> IRSPLR
```

ITC remains later because it postprocesses duplicate metadata. IRSPLR remains last
because unreadable metadata intentionally continues to form inspection.

Implementation status: all five specialized document-row branches are complete in
their dedicated batch-row modules.

### Phase 6F: Run-level dispatch

Implementation status: completed in `document_run_dispatch.py`.

The repeated document-only `process_rows()` branches now use a data-described batch
invocation while preserving the public signature, precedence, callbacks, exact batch
arguments, dataframe shapes, and early returns.

### Phase 6G: Shared SMD/DAR and outer-loop decomposition

Counsel/main sequencing, deferral, progress, session loss, error reporting, and timing
are the last batch-level seams. They should not move together in one change.

Implementation status: the first slice is complete in `shared_run_dispatch.py`.
Counsel/defer/window-cleanup/main execution and its throughput summary now return an
immutable outcome. Final success state, Excel error reporting, and the broad
exception boundary remain in `process_rows()`. The `process_batch()` outer loop is
unchanged.

The second slice is complete in `shared_run_finalization.py`. Success state and
optional Excel error-report output now delegate through a thin router wrapper.
The broad exception boundary remains in `process_rows()`, including its handling of
report-write failures.

The third slice centralizes only progress callback eligibility and invocation in
`batch_policy.emit_batch_progress()`. `process_batch()` retains all three call
locations, counters, `finally`, session-loss, and break behavior.

The fourth slice moves only post-loop throughput calculation and exact summary
logging into `batch_throughput.py`. The router retains the positive-count gate,
clock placement, counters, accumulated duration, and return values.

The fifth slice extends `session_loss_policy.py` with row-level session-loss logging,
remaining-row marking, error-entry creation, and an immutable stop outcome.
`process_batch()` retains the exception clause, `stop_batch`, `finally`, forced
progress, and `break`.

The sixth slice moves generic row-error logging, mode-specific metadata recording,
status buffering, and error-entry creation into `batch_row_error.py`. Best-effort
driver close/window focus remains in the router after the helper call.

The seventh slice moves completed-status handling, validation, and the `PROCESSING`
transition into `batch_row_preflight.py`. `process_batch()` retains row lookup,
`continue`, LNI assignment, the start clock, and all later dispatch.

The eighth slice moves form-status replacement, end-clock calculation, immutable
duration/count increments, and per-LNI log formatting into
`batch_row_finalization.py`. The router retains refresh retry, counter mutation, log
placement, and exceptions.

## Explicitly deferred behavior fixes

This review does not authorize:

- changing failed session prechecks that currently retry and return `False`;
- guaranteeing cleanup with `finally` after form-fill exceptions;
- making result-click success observable;
- propagating swallowed result/popup session errors;
- changing duplicate archive/process policy;
- consolidating status strings;
- changing progress or throughput counting;
- changing error-report location or format;
- changing legacy flag precedence;
- removing compatibility parameters.

Each is a separate product or reliability decision after modularization contracts are
stable.

## Approval recommendation

Phase 6G is complete after eight implementation slices and an architecture
checkpoint. The recommended next gate is Phase 7A characterization only for the
remaining document-outcome call-site block. No Selenium-adjacent extraction is
authorized without a later explicit agreement. See
`PHASE_6G_ARCHITECTURE_CHECKPOINT.md`.

Phase 7A is now complete with eight call-site tests and no production source change.
Phase 7B subsequently extracted the selector-free document-outcome dispatcher while
retaining shared search, form open/retry, status writes, lifecycle control, and
driver cleanup in the router. The subsequent checkpoint recommends
characterization-only Phase 8A for the remaining batch form-transition call site.
Phase 8A is now complete with eight dedicated tests and no production source change.
Phase 8B subsequently extracted the approved selector-free transition wrapper while
retaining status application, finalization, exceptions, driver cleanup, and
outer-loop lifecycle in the router. The subsequent checkpoint concludes that the
remaining method is an appropriate visible controller and recommends no further
batch-code movement. The next useful phase is a documentation-only developer
mode-integration guide. See `PHASE_8B_ARCHITECTURE_CHECKPOINT.md`.

Phase 9A subsequently completes the documentation-only developer guide. No batch or
Selenium code moved. See `MODE_DEVELOPER_INTEGRATION_GUIDE.md`.

The selective 2026-07-28 sync centralizes compatible ChromeDriver resolution and
adds parser/compliance tests without changing batch orchestration. The full offline
suite now passes 381 tests. See `RECENT_PRODUCTION_SYNC_2026-07-28.md` and
`RECENT_PRODUCTION_SYNC_2026-08-07.md`. The August sync did not change batch
orchestration boundaries.
