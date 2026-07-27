# Phase 6E: MNSUTB Batch-Row Wrapper

Status: MNSUTB Phase 6E slice complete  
Scope: one behavior-preserving MNSUTB document-row wrapper

## Outcome

This Phase 6E slice moves only the MNSUTB-specific preparation sequence from
`CaseLawRouter.process_batch()` into
`core/router_modes/mnsutb_batch_row.py`.

The extracted function preserves the existing attempted metadata record, LNI search,
short-circuited availability check, search-failure record, metadata extraction,
missing-metadata record and warning, extracted record, and matching-result click.

It returns an immutable `MnsutbRowOutcome` with the metadata, continuation decision,
and optional row status. `CaseLawRouter.process_mnsutb_document_row()` is a thin
compatibility wrapper.

## Boundary retained by `process_batch()`

The outer method still owns dataframe iteration, status-buffer mutation, loop control,
mode selection, form processing, recovery, final status replacement, timing,
throughput counts, exceptions, progress, and early termination.

The MNSUTB module imports no Selenium, pandas, router class, or shared mutable buffer.
Dependency failures propagate to the unchanged outer batch exception boundary.

## Verification

`tests/test_mnsutb_batch_row.py` adds seven no-driver tests covering success, search
short-circuiting, result unavailability, missing metadata, exception propagation,
router delegation, and dependency isolation.

The focused mode-wrapper, policy, batch, process-row, and handler suite passes 55
tests. The complete offline suite passes 260 tests.

No selector, wait, retry, form-routing, workbook, browser, staging, or production
backup behavior was changed or exercised.

## Subsequent compliance change

After this behavior-preserving batch-row slice, an explicit business requirement
changed MNSUTB Source Detail from `Order` to `Table-(5-day spec source)`. The change
is implemented in the metadata extractor and does not alter this batch-row wrapper.
See `MNSUTB_SOURCE_DETAIL_COMPLIANCE.md`.

## Next gate

The next separately approved Phase 6E slice may extract only ITC. That wrapper must
explicitly preserve `postprocess_metadata()` between extraction and the final
`Extracted` metadata record. IRSPLR remains deferred because missing metadata
intentionally continues to form inspection.

The ITC slice was subsequently completed within that boundary. See
`ITC_BATCH_ROW_PHASE_6E.md`.
