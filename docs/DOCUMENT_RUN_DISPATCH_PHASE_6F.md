# Phase 6F: Document-Only Run Dispatch

Status: complete  
Scope: repeated document-only branches in `CaseLawRouter.process_rows()`

## Outcome

Phase 6F moves the five document-only run branches into
`core/router_modes/document_run_dispatch.py`.

The dispatcher:

- selects the first active document flag using legacy precedence;
- returns `None` when no document mode is active;
- preserves MSPB's filtered counsel/main dataframes;
- preserves full-dataframe copies for ITC, IRSPLR, OHTAX0, and MNSUTB;
- emits the existing count/start/status/processed/summary messages;
- calls exactly one `process_batch()` with the existing positional arguments and
  mode-specific keyword flag;
- returns an immutable `DocumentRunOutcome` for the existing early return.

`CaseLawRouter.dispatch_document_run()` is a thin compatibility wrapper.

## Preserved precedence

```text
mspb > itc > irsplr > ohtax0 > mnsutb
```

Contradictory document flags therefore continue to choose MSPB. DAR and WC flags are
forwarded to the selected batch but do not make the document dispatcher handle the
shared SMD/DAR path.

## Boundary retained by `process_rows()`

`process_rows()` still owns:

- assigning `self.full_df`;
- initial `filter_mapping_data()` execution;
- the entire counsel/defer/cleanup/main sequence;
- shared-run status and timing summaries;
- success state and success callback;
- optional Excel error-report creation;
- the broad exception boundary and empty-dataframe fallback.

Document batch errors propagate from the dispatcher into that unchanged exception
boundary.

The dispatcher imports no Selenium, pandas, router class, filesystem API, or shared
mutable buffer. It relies only on dataframe-like objects supplied by the caller.

## Verification

`tests/test_document_run_dispatch.py` adds seven no-driver tests covering:

- exact dispatch for all five document modes;
- dataframe shape and `process_batch()` arguments;
- contradictory-flag precedence;
- no-document fallthrough;
- zero-count summary behavior;
- error propagation;
- router delegation and module isolation.

All seven existing direct `process_rows()` characterization tests continue to pass.
The focused dispatch/orchestration suite passes 45 tests, and the full offline suite
passes 286 tests.

No selector, browser, staging route, workbook write, or production-backup operation
was performed.

## Next gate

The first Phase 6G slice is now complete in `shared_run_dispatch.py`. It isolates
counsel/defer/window-cleanup/main execution while leaving success state, reporting,
and the broad exception boundary in `process_rows()`. See
`SHARED_RUN_DISPATCH_PHASE_6G.md`.
