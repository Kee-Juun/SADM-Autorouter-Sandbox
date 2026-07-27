# Phase 6E: ITC Batch-Row Wrapper

Status: ITC Phase 6E slice complete  
Scope: one behavior-preserving ITC document-row wrapper

## Outcome

This Phase 6E slice moves only the ITC-specific row-preparation sequence from
`CaseLawRouter.process_batch()` into
`core/router_modes/itc_batch_row.py`.

The extracted function preserves:

1. the `Attempted` metadata record;
2. LNI search and short-circuited result-availability check;
3. search-failure recording and outcome;
4. raw ITC metadata extraction;
5. missing-raw-metadata recording, warning, and skip outcome;
6. duplicate metadata postprocessing;
7. the `Extracted` record using the postprocessed value;
8. matching-result selection.

It returns an immutable `ItcRowOutcome`. `CaseLawRouter.process_itc_document_row()`
is a thin compatibility wrapper.

## ITC-specific contract

Postprocessing remains strictly between raw extraction and the final metadata record:

```text
extract -> postprocess -> record Extracted -> click result
```

Only the raw extraction result is checked for missing metadata. For strict legacy
equivalence, a falsey value returned by `postprocess_metadata()` is still recorded as
`Extracted`, selected through, and returned for form processing. This behavior is
preserved, not endorsed as a future reliability policy.

## Boundary retained by `process_batch()`

The outer method still owns dataframe iteration, shared status-buffer mutation, loop
control, mode precedence, form opening and recovery, final status replacement,
timing, throughput, exceptions, progress, and early termination.

The ITC module imports no Selenium, pandas, router class, or shared mutable buffer.
Postprocessing and other dependency failures propagate to the existing outer
exception boundary.

## Verification

`tests/test_itc_batch_row.py` adds eight no-driver tests covering exact success call
order, postprocessed metadata forwarding, falsey postprocess results, search
short-circuiting, result unavailability, missing raw metadata, exception propagation,
router delegation, and module isolation.

The focused mode-wrapper, policy, batch, process-row, handler, and integration suite
passes 65 tests. The complete offline suite passes 271 tests.

No selector, wait, retry, form-routing, workbook, browser, staging, or production
backup behavior was changed or exercised.

## Next gate

The final separately approved Phase 6E slice may extract only IRSPLR. Its wrapper must
preserve unreadable-PDF fallback construction and continue to matching-result and
form inspection rather than returning a skip outcome.

The IRSPLR slice was subsequently completed within that boundary, completing Phase
6E. See `IRSPLR_BATCH_ROW_PHASE_6E.md`.
