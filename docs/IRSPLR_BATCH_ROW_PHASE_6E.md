# Phase 6E: IRSPLR Batch-Row Wrapper

Status: IRSPLR slice and Phase 6E complete  
Scope: one behavior-preserving IRSPLR document-row wrapper

## Outcome

The final Phase 6E slice moves only the IRSPLR-specific row-preparation sequence from
`CaseLawRouter.process_batch()` into
`core/router_modes/irsplr_batch_row.py`.

The extracted function preserves:

1. the `Attempted` metadata record;
2. LNI search and short-circuited result-availability check;
3. search-failure recording and stop outcome;
4. IRSPLR metadata extraction;
5. unreadable-PDF fallback construction from filename and court hints;
6. `Unreadable PDF Fallback` metadata recording;
7. continued matching-result selection and form inspection;
8. normal `Extracted` recording when metadata is available.

It returns an immutable `IrsplrRowOutcome`.
`CaseLawRouter.process_irsplr_document_row()` is a thin compatibility wrapper.

## IRSPLR-specific contract

Unlike the other document modes, missing extracted metadata does not skip the row.
The wrapper constructs fallback metadata, records it, clicks the matching result, and
returns `continue_to_form=True`.

For strict legacy equivalence, even a falsey fallback-builder result is recorded with
`Unreadable PDF Fallback` and continues. This is preserved behavior, not a new
reliability policy.

The fallback-builder import now belongs to the IRSPLR wrapper rather than
`smducar_router.py`.

## Boundary retained by `process_batch()`

The outer method still owns dataframe iteration, shared status-buffer mutation, loop
control, mode precedence, form opening and recovery, final status replacement,
timing, throughput, exceptions, progress, and early termination.

The IRSPLR wrapper imports no Selenium, pandas, router class, or shared mutable
buffer. Fallback and dependency failures propagate to the unchanged outer exception
boundary.

## Verification

`tests/test_irsplr_batch_row.py` adds eight no-driver tests covering normal metadata,
fallback construction and call order, falsey fallback continuation, search
short-circuiting, result unavailability, fallback exceptions, router delegation, and
module isolation.

The focused mode-wrapper, policy, batch, process-row, handler, and integration suite
passes 73 tests. The complete offline suite passes 279 tests.

No selector, wait, retry, form-routing, workbook, browser, staging, or production
backup behavior was changed or exercised.

## Phase 6E completion

All five specialized document-row preparation branches now have dedicated wrappers:

```text
MSPB -> OHTAX0 -> MNSUTB -> ITC -> IRSPLR
```

`process_batch()` remains the outer runtime implementation and retains shared state,
form processing, exceptions, timing, and progress.

## Next gate

Phase 6F may address repeated document-only dispatch in `process_rows()`. It should
begin with the already characterized exact arguments, status callbacks, branch
precedence, and early returns, and must not move Selenium logic.

Phase 6F was subsequently completed within that boundary. See
`DOCUMENT_RUN_DISPATCH_PHASE_6F.md`.
