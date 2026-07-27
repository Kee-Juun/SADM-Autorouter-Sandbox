# Phase 6G Architecture Checkpoint

Status: complete  
Scope: remaining `CaseLawRouter.process_batch()` orchestration after eight slices

## Decision

Phase 6G is complete. No code moved during this checkpoint.

The remaining 226-line `process_batch()` method is now primarily an explicit
orchestration shell around already extracted policies and outcomes. The largest
remaining blocks are Selenium-adjacent and should not be consolidated under the
behavior-preserving Phase 6G authorization.

## Measured remaining blocks

| Lines | Approximate size | Responsibility | Classification |
| --- | ---: | --- | --- |
| 2169-2180 | 12 | alert cleanup, counters, initial progress | Mixed lifecycle |
| 2181-2197 | 17 | row lookup, preflight call, `continue`, start clock | Outer-loop control |
| 2199-2217 | 19 | metadata slots, row predicates, handler selection | Mode dispatch |
| 2218-2282 | 65 | five document-wrapper calls and outcome application | Selenium-adjacent orchestration |
| 2283-2286 | 4 | shared SMD/DAR LNI search and failure status | Selenium-adjacent |
| 2288-2319 | 32 | form opening and refresh retry | Selenium-adjacent |
| 2321-2331 | 11 | finalization outcome, counters, row timing log | Extracted boundary application |
| 2334-2382 | 49 | session loss, generic error, cleanup, `finally`, stop | Mixed exception/lifecycle |
| 2384-2393 | 10 | throughput helper and return | Extracted boundary application |

Line numbers describe the checkpoint source and may shift in later edits.

## Boundaries completed in Phase 6G

1. document-only run dispatch;
2. shared SMD/DAR counsel/defer/cleanup/main dispatch;
3. shared-run success and optional report finalization;
4. batch progress emission;
5. batch throughput calculation and summary;
6. router-session-loss row outcome;
7. generic row-error recording;
8. completed/invalid/processable row preflight;
9. post-form row status/duration finalization and timing log.

`process_rows()` is now 59 lines. `process_batch()` is 226 formatted lines.

## Current evidence

- 13 direct `process_batch()` characterization tests;
- 37 direct tests across the five document-row wrappers;
- 8 handler registry/precedence tests;
- 2 handler integration tests;
- 10 form-opening/retry characterization tests;
- dedicated tests for each Phase 6G helper and outcome;
- 330 offline tests passing.

This coverage strongly protects current behavior but is distributed across layers.
The 65-line document-wrapper call-site block does not yet have a dedicated boundary
suite for contradictory row signals, every early outcome, predicate/handler failure
order, and exact metadata-slot construction.

## Deferred Selenium-adjacent candidates

### Document outcome application

Potential future boundary: select and invoke one of the five existing document-row
wrappers, then return metadata slots plus a continue/skip outcome.

Risk: medium-high. Although the new boundary would contain no selectors, the invoked
wrappers perform search, extraction, result selection, and other browser-adjacent
work.

### Shared SMD/DAR search

Potential future boundary: shared `handle_lni_search()` fallback and failure status.

Risk: high. This is direct browser-routing behavior and should remain deferred.

### Form opening and refresh retry

Potential future boundary: call `open_and_process_form()`, evaluate recoverability,
and invoke `_refresh_and_retry_current_row()`.

Risk: high. These calls coordinate browser state, recursion, tab lifecycle, and form
routing. They are already separately modular below `process_batch()` and need not
move merely to reduce line count.

### Generic driver cleanup

Potential future boundary: close the active driver window and refocus the first
handle after a generic row error.

Risk: medium. It is small, directly browser-dependent, and not worth moving alone.

## Recommended Phase 7A

If further modularization is desired, begin with characterization only:

- contradictory row predicates at the `process_batch()` call site;
- each wrapper outcome with `continue_to_form=False`;
- exact status write and `finally` progress after each skip;
- exact five-slot metadata construction for form opening;
- wrapper/predicate failure propagation into generic error recording;
- proof that shared SMD/DAR search is selected only when no document handler exists.

Do not move code in Phase 7A. After those tests pass, separately approve or reject a
selector-free but Selenium-adjacent document-outcome dispatcher.

Phase 7A is now complete with eight dedicated tests. See
`PHASE_7A_DOCUMENT_OUTCOME_CHARACTERIZATION.md`. No production code moved.

Phase 7B subsequently moved only the characterized document selection, wrapper
invocation, and metadata normalization into an immutable selector-free dispatcher.
`process_batch()` is now 163 formatted lines. The shared search, form open/retry,
exception/lifecycle, and driver-cleanup boundaries remain in the router. See
`PHASE_7B_DOCUMENT_OUTCOME_DISPATCH.md`.

## Validation boundary

No live browser or staging validation has been performed. That remains acceptable
for Phase 6G because no selector or form-routing implementation moved. Any later
Selenium-adjacent consolidation should define whether a staging smoke test is
required before implementation.

No production-backup file, live route, external system, or workbook was touched
during this checkpoint.
