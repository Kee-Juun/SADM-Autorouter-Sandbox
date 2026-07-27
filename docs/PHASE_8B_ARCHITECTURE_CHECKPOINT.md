# Phase 8B Architecture Checkpoint

Status: complete; documentation only  
Scope: remaining `CaseLawRouter.process_batch()` orchestration after Phase 8B

## Decision

Phase 8B is complete. No production code moved during this checkpoint.

The remaining 146-line `process_batch()` is an appropriate outer-loop controller.
It no longer contains a document-mode implementation or a shared form-transition
implementation. It applies immutable outcomes, preserves visible loop control, and
owns the exception, progress, counter, and return-value lifecycle.

Further batch extraction is not recommended merely to reduce line count. It would
hide control flow without producing a clearer reusable mode boundary.

## Current measured structure

| Item | Value |
| --- | ---: |
| `core/smducar_router.py` | 3,480 lines |
| `process_batch()` | 146 formatted lines |
| `process_rows()` | 59 lines |
| Router class methods | 156 |
| `core/router_modes/` Python modules | 41 |
| Full offline suite | 363 tests |

## Remaining `process_batch()` map

Line numbers describe the Phase 8B checkpoint source and may shift later.

| Lines | Responsibility | Classification |
| --- | --- | --- |
| 2175-2187 | alert cleanup, counters, clocks, initial progress | Batch lifecycle |
| 2189-2203 | row lookup, preflight outcome, `continue`, row clock | Outer-loop control |
| 2205-2229 | document dispatch and early outcome application | Extracted boundary application |
| 2230-2244 | form-transition wrapper invocation | Extracted boundary application |
| 2247-2263 | transition application, finalization, counters, duration log | Outer-loop state application |
| 2267-2293 | session-loss and generic-error selection, driver cleanup | Mixed policy and direct Selenium |
| 2295-2308 | forced progress and stop/break control | Outer-loop lifecycle |
| 2310-2319 | throughput summary and return | Extracted boundary application |

## Why the outer loop should remain visible

The method now makes the critical lifecycle easy to read in one place:

```text
preflight
  -> document outcome
  -> form-transition outcome
  -> finalization
  -> exception policy
  -> always progress
  -> optional stop
  -> throughput
```

The following are controller responsibilities rather than mode responsibilities:

- dataframe iteration and row lookup;
- `continue` and `break` placement;
- applying row statuses to shared buffers;
- processed-count and duration accumulation;
- exception-class selection;
- per-row and forced-final progress;
- batch summary gating and returned totals.

## Direct driver cleanup

The generic-error branch still best-effort closes the active driver window and
focuses the first remaining handle. This block:

- directly mutates Selenium state;
- is not mode-specific;
- is only a few lines;
- is already characterized after successful error recording;
- deliberately swallows cleanup failure.

Moving it alone would not advance router-mode modularity. Changing its `except`
style, target-window policy, or failure handling would be a separate reliability
change rather than a behavior-preserving extraction.

## Mode-aware compatibility that remains

`process_batch()` still forwards:

- legacy mode flags to the document dispatcher and form-transition wrapper;
- the four row predicates and handler selector as injectable dependencies;
- `mspb_mode` plus row predicates to generic error recording.

These preserve existing patch points, precedence, and metadata/error behavior. They
do not represent embedded mode implementations.

## Recommended next phase

The next useful step is documentation-only Phase 9A: a developer mode-integration
guide. It should explain, in implementation order:

1. registry identity and legacy flag compatibility;
2. workflow scope and document-run dispatch;
3. row predicates and metadata extraction;
4. row-handler registration and precedence;
5. document-row outcome wrappers;
6. form dispatch and Selenium compatibility wrappers;
7. status, metadata-buffer, and error-report contracts;
8. required direct, call-site, and full-suite tests;
9. business-compliance constants such as MNSUTB Source Detail;
10. when staging validation is required.

No additional batch refactor is needed before that guide.

Phase 9A is now complete. See `MODE_DEVELOPER_INTEGRATION_GUIDE.md`. No runtime code
changed.

## Safety record

Only the Sandbox project was inspected and documented. No live browser, staging
route, external routing action, workbook write, Selenium selector, production code,
or production backup was touched.

MNSUTB Source Detail remains exactly `Table-(5-day spec source)`.
