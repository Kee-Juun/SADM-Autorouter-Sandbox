# Phase 6D: MSPB Batch-Row Wrapper

Status: complete  
Scope: one behavior-preserving MSPB document-row wrapper

## Outcome

Phase 6D moves only the MSPB-specific preparation sequence from
`CaseLawRouter.process_batch()` into
`core/router_modes/mspb_batch_row.py`.

The extracted function performs the existing:

1. `Attempted` metadata record;
2. LNI search and result-availability check;
3. `Search Failed` metadata record;
4. MSPB metadata extraction;
5. missing-metadata record and warning;
6. `Extracted` metadata record;
7. matching-result click.

It returns an immutable `MspbRowOutcome` containing the extracted metadata, whether
form processing should continue, and any row status required by the outer loop.
`CaseLawRouter.process_mspb_document_row()` is a thin compatibility wrapper.

## Boundary retained by `process_batch()`

The outer method still owns:

- dataframe iteration and original indices;
- `status_updates_buffer` mutation;
- the `continue` decision after an MSPB skip or search failure;
- validation and `PROCESSING` status;
- mode-handler selection and precedence;
- form opening, recovery, and final status replacement;
- timing and throughput counts;
- all generic and session-loss exception handling;
- progress callbacks and early batch termination.

The wrapper does not import or mutate shared status or metadata buffers. Dependency
errors intentionally propagate to the unchanged outer exception boundary.

## Verification

`tests/test_mspb_batch_row.py` adds seven no-driver tests covering:

- successful search, extraction, recording, and result selection;
- search short-circuit behavior;
- unavailable-result behavior;
- missing-metadata outcome;
- exception propagation;
- router compatibility delegation;
- module dependency isolation.

The existing batch characterization, policy, process-row, and handler tests continue
to pass. The complete offline suite passes 246 tests.

No selector, wait, retry, form-routing, workbook, browser, staging, or production
backup behavior was changed or exercised.

## Next gate

Phase 6E may extract only the OHTAX0 document-row branch using the same outcome
boundary. OHTAX0 should be approved and verified independently before MNSUTB, ITC,
or IRSPLR is moved.

The OHTAX0 slice was subsequently completed within that boundary. See
`OHTAX0_BATCH_ROW_PHASE_6E.md`.
