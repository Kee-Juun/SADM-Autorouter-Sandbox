# Phase 6G: Shared SMD/DAR Run Dispatch

Status: first slice complete  
Scope: shared counsel/defer/window-cleanup/main orchestration in
`CaseLawRouter.process_rows()`

## Outcome

The first Phase 6G slice moves the shared SMD/DAR run sequence into
`core/router_modes/shared_run_dispatch.py`.

The dispatcher preserves:

- counsel batch execution before main-opinion execution;
- exact DAR and WC flag forwarding to both batches;
- deferral of main rows whose required counsel did not finish cleanly;
- the existing counsel and main status callbacks;
- best-effort closing of extra browser windows between batches;
- the existing processing-count, duration, average, and hourly-estimate logs;
- propagation of batch and deferral errors to the existing outer exception boundary.

It returns an immutable `SharedRunOutcome`. The router exposes
`dispatch_shared_run()` as a thin compatibility wrapper.

## Boundary retained by `process_rows()`

`process_rows()` still owns:

- assigning `self.full_df`;
- initial `filter_mapping_data()` execution;
- document-only dispatch and its early return;
- final success timestamps, message, and callback for shared runs;
- optional Excel error-report creation;
- the broad exception boundary and empty-dataframe fallback.

The dispatcher does not import Selenium, pandas, the router class, configuration, or
shared status/metadata buffers. Browser interaction is limited to invoking the
existing driver window API supplied by the router; no selector, form-routing, save,
or staging behavior moved.

## Verification

`tests/test_shared_run_dispatch.py` adds seven no-driver tests covering:

- exact counsel/defer/main call order and outcome values;
- DAR/WC forwarding and status callback order;
- closing all extra windows;
- best-effort cleanup failure followed by main execution;
- zero-count summary behavior;
- counsel error propagation before deferral;
- router delegation and module isolation.

The focused orchestration suite passes 45 tests. The full offline suite passes 293
tests. Expected warnings and errors come from deliberate failure-path
characterization.

No live browser, staging route, workbook write, external routing action, or
production-backup operation was performed.

## Next gate

The separate finalization/reporting slice is now complete in
`shared_run_finalization.py`. See `SHARED_RUN_FINALIZATION_PHASE_6G.md`. The next
gate is an outer-loop boundary review, not an authorization to move Selenium routing.
