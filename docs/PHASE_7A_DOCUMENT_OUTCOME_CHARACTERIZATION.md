# Phase 7A: Document-Outcome Call-Site Characterization

Status: complete; characterization only  
Scope: the document-wrapper selection and outcome block in `process_batch()`

## Outcome

Phase 7A adds
`tests/test_document_outcome_callsite_characterization.py` without changing
production source.

The eight no-driver tests execute the 65-line call-site block through
`CaseLawRouter.process_batch()` and lock:

- all five document wrappers;
- exact five-slot metadata construction for `open_and_process_form()`;
- suppression of shared SMD/DAR search when a document handler exists;
- every `continue_to_form=False` status write and `finally` progress sequence;
- MSPB precedence when every mode flag and row predicate is true;
- ITC precedence when every row predicate is true without MSPB;
- shared search only when no document handler exists;
- shared-search failure status and early skip;
- wrapper failure entering generic error recording before driver cleanup;
- predicate failure entering generic error recording before driver cleanup.

## Current call-site contracts

### Eager predicates

All four row predicates are evaluated before handler selection, even when
`mspb_mode=True` ultimately wins. This is preserved behavior, not a recommendation
to keep eager evaluation forever.

### Precedence

The effective row-handler precedence remains:

```text
mspb > itc > irsplr > ohtax0 > mnsutb > shared SMD/DAR
```

### Metadata slots

Exactly one of these form arguments is populated for a continuing document outcome:

```text
mspb_metadata
itc_metadata
irsplr_metadata
ohtax0_metadata
mnsutb_metadata
```

The other four remain `None`. Shared SMD/DAR supplies all five as `None`.

### Early outcomes

When a wrapper returns `continue_to_form=False`, the call site:

1. writes the wrapper's `row_status`;
2. skips shared search and form opening;
3. does not increment processed count or duration;
4. still emits per-row progress through `finally`.

### Failures

Wrapper or predicate failures enter the existing generic error recorder, then
best-effort driver cleanup, then row progress in `finally`. Failure inside the error
recorder remains separately characterized as preventing driver cleanup.

## Verification

- new Phase 7A suite: 8 tests passing;
- combined mode/form boundary set: 78 tests passing;
- full offline suite: 338 tests passing.

Expected warning/error logs in the broader set are deliberate failure-path tests.

No browser, staging route, external routing action, workbook write, production
source refactor, or production-backup operation was performed.

## Optional Phase 7B design

The evidence supports—but does not authorize—a selector-free document-outcome
dispatcher that:

- receives the router, row, index, LNI, flags, and predicate results;
- preserves eager predicate evaluation and current precedence;
- invokes exactly one existing document-row wrapper;
- returns an immutable outcome containing handler key, five metadata slots,
  `continue_to_form`, and row status;
- leaves the status write, `continue`, shared search, form opening, retry, counters,
  exceptions, progress, and driver cleanup in `process_batch()`.

Although the dispatcher would contain no selectors, it would invoke wrappers that
perform browser-adjacent work. Phase 7B therefore requires separate explicit
approval. A staging-smoke decision should be made before implementation; no live
validation is authorized by this document.

## Phase 7B completion note

Phase 7B was subsequently approved and implemented. The selector-free dispatcher
preserves the contracts above while leaving shared search, form open/retry, status
writes, exceptions, progress, and driver cleanup in `process_batch()`. See
`PHASE_7B_DOCUMENT_OUTCOME_DISPATCH.md`. No live staging validation was performed.
