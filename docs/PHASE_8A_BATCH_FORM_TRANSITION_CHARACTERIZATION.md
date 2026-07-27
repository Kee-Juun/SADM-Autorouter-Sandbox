# Phase 8A: Batch Form-Transition Characterization

Status: complete; characterization only  
Scope: the shared-search/form-open/retry call site in `process_batch()`

## Outcome

Phase 8A adds
`tests/test_batch_form_transition_callsite_characterization.py` without changing
production source.

The eight no-driver tests execute the remaining browser-controlled transition
through `CaseLawRouter.process_batch()` using mocks. They lock:

- shared LNI search occurring before form opening;
- exact shared-path form arguments and five empty metadata slots;
- shared-search failure status, early skip, and row progress;
- document-handler suppression of shared search;
- exact document-path form flags and metadata forwarding;
- non-recoverable form status bypassing refresh retry;
- exact recoverable retry arguments, flags, metadata, and initial status;
- replacement of the initial status by the retry result before finalization;
- generic handling for failures in shared search, form open, retry decision, and
  retry invocation;
- generic error recording before best-effort driver cleanup and `finally` progress;
- router-session loss using its stop path without generic cleanup.

## Locked transition order

For a shared SMD/DAR row:

```text
shared LNI search
  -> form open
  -> retry eligibility decision
  -> optional refresh/retry
  -> row finalization
```

For a continuing document-mode row, the document wrapper replaces shared LNI search;
the remaining form-open/retry/finalization order is identical.

Shared-search failure writes `ERROR: LNI NOT FOUND` and skips form opening, retry
decision, retry invocation, and finalization. Per-row progress still occurs through
the outer `finally`.

## Retry contract

The retry decision receives the initial `form_status` and row index. When eligible,
`_refresh_and_retry_current_row()` receives:

- the same row, full dataframe, row index, and file path;
- the initial form status;
- unchanged DAR, WC, and MSPB flags;
- the same five document metadata slots used for the first form opening.

The retry return value replaces the initial form status before
`finalize_batch_row()`.

## Failure contract

Ordinary failures at any of the four transition points enter the existing generic
row-error recorder. Only after recording succeeds does the router best-effort close
the active window and focus the first remaining handle. Progress then occurs in
`finally`.

`RouterSessionLostError` remains distinct: it enters the session-loss policy, marks
the batch to stop, does not invoke generic cleanup, emits row progress, forces final
batch progress, and breaks.

## Verification

- new Phase 8A suite: 8 tests passing;
- combined mode/form boundary: 94 tests passing;
- full offline suite: 354 tests passing.

Expected warning and error logs are deliberate failure-path tests.

## Safety and next gate

Only a test file and documentation were added in the Sandbox project. No production
source, Selenium selector, browser operation, live route, workbook, external system,
or production backup was changed.

MNSUTB Source Detail remains exactly `Table-(5-day spec source)`.

The evidence supports a possible Phase 8B selector-free transition wrapper, but does
not authorize it. Such a wrapper would invoke shared search, form opening, and
refresh/retry browser behavior. Phase 8B therefore requires explicit approval and a
separate staging-smoke decision.

Phase 8B was subsequently approved and implemented without live staging validation.
The retained router boundary and all verification results are recorded in
`PHASE_8B_BATCH_FORM_TRANSITION.md`.
