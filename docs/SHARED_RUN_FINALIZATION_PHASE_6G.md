# Phase 6G: Shared-Run Finalization

Status: second slice complete  
Scope: shared-run success state and optional legacy error-report output

## Outcome

The second Phase 6G slice moves the success/report side effects from
`CaseLawRouter.process_rows()` into
`core/router_modes/shared_run_finalization.py`.

The extracted function preserves:

- the success timestamp;
- resetting the success-message dismissed flag;
- the existing success log message;
- the optional `Success!` callback;
- creation of an Excel error report only when error entries exist;
- the legacy Downloads folder and timestamped filename;
- propagation of folder or workbook failures to the caller.

`CaseLawRouter.finalize_shared_run()` is a thin compatibility wrapper that supplies
the existing global error-entry list.

## Boundary retained by `process_rows()`

`process_rows()` still owns:

- assigning `self.full_df`;
- initial counsel/main filtering;
- document-only dispatch and early return;
- shared SMD/DAR dispatch;
- returning the resulting dataframes;
- classifying normal-outcome exception messages;
- exception logging;
- conversion of every caught failure, including report-write failures, to two empty
  dataframes.

The finalization module imports no Selenium, router class, configuration, or shared
mutable buffer. It receives error entries explicitly.

## Verification

`tests/test_shared_run_finalization.py` adds seven no-driver tests covering:

- exact success state, message, and callback;
- absence of a callback;
- no report for an empty error list;
- exact legacy report folder, filename, and Excel arguments;
- report-write error propagation after success state is set;
- the unchanged outer `process_rows()` failure fallback;
- router delegation and module isolation.

The focused orchestration suite passes 52 tests. The full offline suite passes 300
tests. Expected error logs are deliberate failure-path characterization.

No live browser, staging route, external routing action, real workbook write, or
production-backup operation was performed.

## Next gate

Keep the 59-line `process_rows()` shell intact unless a later review identifies a
materially useful boundary. The next outer-loop review subsequently centralized only
progress callback policy in `batch_policy.py`; see `BATCH_PROGRESS_PHASE_6G.md`.
