# Phase 6E: OHTAX0 Batch-Row Wrapper

Status: first Phase 6E slice complete  
Scope: one behavior-preserving OHTAX0 document-row wrapper

## Outcome

This Phase 6E slice moves only the OHTAX0-specific preparation sequence from
`CaseLawRouter.process_batch()` into
`core/router_modes/ohtax0_batch_row.py`.

The extracted function preserves the existing:

1. `Attempted` metadata record;
2. LNI search and short-circuited result-availability check;
3. `Search Failed` metadata record and row outcome;
4. OHTAX0 metadata extraction;
5. missing-metadata record, warning, and skip outcome;
6. `Extracted` metadata record;
7. matching-result click.

It returns an immutable `Ohtax0RowOutcome` containing the metadata, whether form
processing should continue, and any row status required by the outer loop.
`CaseLawRouter.process_ohtax0_document_row()` remains a thin compatibility boundary.

## Boundary retained by `process_batch()`

As with MSPB, the outer method still owns:

- dataframe iteration and original indices;
- shared status-buffer mutation and loop `continue`;
- row validation, mode selection, and precedence;
- form opening, recovery, and final status replacement;
- timing and throughput counts;
- generic and session-loss exception handling;
- progress callbacks and early batch termination.

The OHTAX0 module imports no Selenium, pandas, router class, or shared mutable buffer.
Dependency failures propagate to the unchanged outer exception boundary.

## Verification

`tests/test_ohtax0_batch_row.py` adds seven no-driver tests for success, search
short-circuiting, result unavailability, missing metadata, exception propagation,
router delegation, and dependency isolation.

The focused wrapper, policy, batch, process-row, and handler suite passes 48 tests.
The complete offline suite passes 253 tests.

No selector, wait, retry, form-routing, workbook, browser, staging, or production
backup behavior was changed or exercised.

## Next gate

The next separately approved Phase 6E slice may extract only MNSUTB. ITC remains
later because it postprocesses duplicate metadata; IRSPLR remains last because its
missing-metadata behavior intentionally continues to form inspection.

The MNSUTB slice was subsequently completed within that boundary. See
`MNSUTB_BATCH_ROW_PHASE_6E.md`.
