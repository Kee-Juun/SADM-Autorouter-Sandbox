# Batch Orchestration Characterization

Status: Phase 8B form-transition wrapper complete  
Scope: direct tests for `CaseLawRouter.process_batch()` and `process_rows()`

## Outcome

Phase 6B added two no-driver characterization suites:

- `tests/test_process_batch_characterization.py`: 12 tests;
- `tests/test_process_rows_characterization.py`: 7 tests.

Together with the existing ITC integration test, `process_batch()` now has 13 direct
tests. `process_rows()` now has 7 direct tests. The full offline suite passes 232
tests.

No method was extracted, wrapped, reordered, or rewritten in this phase.

## Locked `process_batch()` contracts

The tests now execute:

- initial alert cleanup;
- supported-batch `0 / total` and per-row progress;
- no progress for an unknown batch label;
- completed-row preservation;
- invalid-LNI short circuit;
- shared SMD/DAR search and form path;
- successful metadata flow for MSPB, ITC, IRSPLR, OHTAX0, and MNSUTB;
- ITC metadata postprocessing;
- document search failure and metadata status recording;
- mode-specific missing-metadata skip statuses;
- IRSPLR unreadable-PDF fallback continuing to form inspection;
- one recoverable-form retry;
- buffered-status precedence over a returned form error;
- generic error status, metadata record, error-log entry, and best-effort window
  cleanup;
- router-session-loss remaining-row propagation, forced final progress, and early
  batch stop;
- processed-count and duration semantics for a normal completed row.

## Locked `process_rows()` contracts

The tests now execute:

- single-batch dispatch for MSPB, ITC, IRSPLR, OHTAX0, and MNSUTB;
- exact mode-specific `process_batch()` arguments and keyword flags;
- document-mode status callbacks and early returns;
- contradictory document flags preserving MSPB precedence;
- SMD/DAR counsel-before-main ordering;
- counsel-dependent main deferral;
- exact DAR/WC flag forwarding;
- cleanup of every extra window between counsel and main;
- final success status and state fields;
- error-report path creation and Excel invocation through patched boundaries;
- filter and document-batch failures returning two empty dataframes.

## Test isolation

The suites:

- construct routers without calling `CaseLawRouter.__init__()`;
- use mock drivers and mode handlers;
- patch dataframe filtering, deferral, filesystem, and Excel output where required;
- clear shared status, metadata, and error buffers after tests;
- create no browser session;
- write no workbook or error report;
- perform no external routing action.

Expected warning/error logs appear during tests because failure branches are being
characterized deliberately.

## Existing behavior preserved, not endorsed

The tests lock several behaviors that may later deserve separate reliability changes:

- unknown batch labels receive no progress callbacks;
- ITC remains row-aware and has no `itc_mode` parameter in `process_batch()`;
- IRSPLR missing metadata continues while four other document modes skip;
- throughput counts exclude completed, invalid, skipped, and failed rows;
- generic errors are swallowed after status/log cleanup;
- `process_rows()` converts broad failures into two empty dataframes;
- document-mode branches return before shared success-state handling;
- MSPB wins contradictory document-mode flags.

Phase 6B does not authorize changing these contracts.

## Subsequent Phase 6C result

Phase 6C subsequently introduced `core/router_modes/batch_policy.py` for:

- the supported progress-label set and progress eligibility;
- completed-row status recognition;
- final form-status replacement policy;
- mode-specific missing-metadata outcomes;
- data-only descriptions of document batch calls.

The helpers import no Selenium, pandas, router class, filesystem API, or shared
mutable buffer. `process_batch()` and `process_rows()` remain the runtime
implementations, and all characterization tests pass after adoption. See
`BATCH_POLICY_PHASE_6C.md`.

## Next gate

Phase 6D subsequently wrapped only the MSPB specialized document-row branch while
leaving the outer loop, global buffers, exception boundaries, progress, and timing in
`process_batch()`. All characterization tests continue to pass. See
`MSPB_BATCH_ROW_PHASE_6D.md`.

The first Phase 6E slice subsequently wrapped OHTAX0 as a separately verified
change. The next slice independently wrapped MNSUTB. Phase 6E may wrap ITC next only
with its postprocessing order explicitly characterized. That ITC slice is now
complete. The final IRSPLR slice preserves fallback continuation and completes Phase
6E. Phase 6F subsequently moved document-only run-level dispatch behind a
non-Selenium outcome boundary. The first Phase 6G slice subsequently moved shared
counsel/defer/window-cleanup/main execution behind another outcome boundary. All
`process_rows()` contracts continue to pass, with seven additional direct
shared-dispatch tests. The second Phase 6G slice moved shared-run success state and
optional error-report output behind a separate boundary, with seven additional
direct tests. The full suite now passes 300 tests.

The third Phase 6G slice centralizes the repeated progress eligibility and callback
invocation in `emit_batch_progress()`. Three additional pure tests cover supported,
unsupported, and missing-callback cases. Existing loop tests continue to lock exact
start, per-row, and forced session-loss progress sequences. The full suite passes 303
tests.

The fourth Phase 6G slice moves post-loop throughput calculation and exact log
formatting into `batch_throughput.py`. Five direct tests lock calculations, elapsed
truncation, clock propagation, module isolation, and division-before-clock behavior.
The integrated batch success test locks the emitted line. The full suite passes 308
tests.

The fifth Phase 6G slice extends the existing non-Selenium session-loss policy with
an immutable batch outcome. Three additional tests lock log/mark/append order and
failure propagation. Existing batch characterization retains `finally`, forced
progress, and early-stop coverage. The full suite passes 311 tests.

The sixth Phase 6G slice moves generic row-error recording into
`batch_row_error.py` while retaining driver cleanup in `process_batch()`. Five
isolated tests cover mode precedence, metadata status, buffers, failures, and module
isolation; an integration test locks failure-before-cleanup with `finally` progress.
The full suite passes 317 tests.

The seventh Phase 6G slice moves completed/invalid/processable row preflight into
`batch_row_preflight.py`. Six direct tests lock exact decisions, order, failures, and
module isolation. Existing batch tests retain `continue`, progress, timing, and
generic-error coverage. The full suite passes 323 tests.

The eighth Phase 6G slice moves post-form status replacement, end-clock calculation,
immutable increments, and per-LNI log formatting into
`batch_row_finalization.py`. Seven direct tests lock ordering, failures, logging, and
module isolation. The integrated batch test locks both timing messages. The full
suite passes 330 tests.

The Phase 6G architecture checkpoint makes no code change. It classifies the
remaining document outcome, shared search, form opening/retry, and driver cleanup
blocks as Selenium-adjacent. Further work should begin with Phase 7A
characterization only.

Phase 7A subsequently adds eight direct `process_batch()` call-site tests for all
five document outcomes, contradictory signals, shared fallback, metadata slots, and
failure order. No production code moved. The full suite passes 338 tests.

Phase 7B adds eight direct contracts for an immutable, selector-free document-row
outcome dispatcher and replaces the characterized call-site branch with that
dispatcher. The combined mode/form boundary passes 86 tests and the full offline
suite passes 346 tests. Shared search, form open/retry, exception handling, progress,
and driver cleanup remain in `process_batch()`. See
`PHASE_7B_DOCUMENT_OUTCOME_DISPATCH.md`.

Phase 8A adds eight no-driver call-site tests for shared-search ordering, exact form
and retry arguments, retry-result finalization, four generic failure points, and
router-session loss. No production code moved. The combined mode/form boundary
passes 94 tests and the full offline suite passes 354 tests. See
`PHASE_8A_BATCH_FORM_TRANSITION_CHARACTERIZATION.md`.

Phase 8B adds nine direct contracts and moves the characterized transition behind an
immutable selector-free outcome. The router retains status writes, `continue`,
finalization, exceptions, driver cleanup, progress, and counters. The combined
mode/form boundary passes 103 tests and the full offline suite passes 363 tests. See
`PHASE_8B_BATCH_FORM_TRANSITION.md`.
