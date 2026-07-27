# Phase 6C: Pure Batch Policy

Status: complete  
Scope: behavior-preserving policy extraction only

## Outcome

Phase 6C adds `core/router_modes/batch_policy.py`, a data-only module for decisions
that were previously repeated inside `CaseLawRouter.process_batch()` and
`CaseLawRouter.process_rows()`.

The module centralizes:

- supported progress callback batch names;
- completed-row recognition;
- replacement of buffered `PROCESSING` with a returned form status;
- mode-specific missing-metadata outcomes;
- document-only batch names, status labels, filtering shape, and legacy flag names.

`process_batch()` and `process_rows()` remain the runtime implementations. Their loop,
branch order, Selenium calls, metadata extraction, exception handling, timing,
progress callbacks, status-buffer writes, and return behavior were not moved.

## Preserved contracts

- Progress remains enabled only for `counsel`, `main`, `mspb`, `itc`, `irsplr`,
  `ohtax0`, and `mnsutb`.
- Only `DONE` and `ALREADY PROCESSED` are completed row statuses.
- A returned noncompleted form status replaces only a buffered `PROCESSING` value.
- MSPB, ITC, OHTAX0, and MNSUTB still skip when required PDF metadata is missing,
  using their exact existing status text.
- IRSPLR still creates unreadable-PDF fallback metadata and continues to inspect the
  form.
- Document-mode dispatch order and exact `process_batch()` arguments remain
  unchanged.

## Isolation

The policy module imports no Selenium, pandas, router class, filesystem API, or shared
mutable status/metadata buffer. Its policy mappings and records are immutable.

`tests/test_batch_policy.py` directly checks all policy values, decisions,
immutability, unknown-key behavior, and forbidden dependencies. Existing
`process_batch()` and `process_rows()` characterization tests verify the adopted
helpers at the runtime boundary. The complete offline suite passes 239 tests.

No browser session, workbook write, staging route, or production-project edit was
performed.

## Next gate

Phase 6D may wrap one specialized document-row branch, preferably MSPB. That phase
must preserve the outer loop, global buffers, exception boundaries, progress, timing,
and current router method signature, and should be approved separately.

Phase 6D was subsequently completed within that boundary. See
`MSPB_BATCH_ROW_PHASE_6D.md`.
