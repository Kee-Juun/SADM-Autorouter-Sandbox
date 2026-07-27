# Safe Router Mode Registry and Wrapper Plan

Status: Phases 1 through 9A and the Phase 9B documentation closeout are complete  
Dependency: read `ROUTER_MODES_ARCHITECTURE.md` first

Documentation entry point: [README.md](README.md)  
Current closeout: [MODULARIZATION_CLOSEOUT.md](MODULARIZATION_CLOSEOUT.md)

## Objective

Introduce one source of truth for mode identity and low-risk metadata while preserving
the existing boolean-based workflow and `CaseLawRouter` behavior. The registry should
make later mode extraction readable without requiring a large rewrite.

## Design constraints

1. Keep `run_automation_workflow()` and `CaseLawRouter` callable exactly as they are
   during the compatibility phases.
2. Do not move or rewrite Selenium selectors, waits, click order, retries, tab cleanup,
   route selection, or save behavior in the registry phase.
3. Preserve legacy flag precedence and unknown-mode fallback behavior.
4. Preserve `wc_mode` parameters where existing callers may depend on their signatures.
5. Keep parsing modules independent of Selenium.
6. Make each phase small enough to review, test, and approve independently.

## Proposed module boundary

Add a data-only module in a later approved phase:

```text
core/router_modes/
    __init__.py
    registry.py
    compatibility.py
```

`registry.py` would define an immutable `ModeSpec` and the active registry.
`compatibility.py` would translate between the canonical mode key and today's flags.
Neither module would import Selenium, PyQt, pandas, or extractor implementations in
the first phase.

### Initial `ModeSpec`

The first version should contain metadata only:

```python
@dataclass(frozen=True)
class ModeSpec:
    key: str
    display_name: str
    router_label: str
    progress_batch: str
    result_label: str
    document_only: bool
```

Possible registry data, preserving current visible text:

| Key | Display name | Router label | Progress batch | Document only |
| --- | --- | --- | --- | --- |
| `smd` | SMD Autorouter | SADM | `main` | No |
| `dar` | DAR Autoruter | DAR | `main` | No |
| `mspb` | MSPB Autorouter | MSPB | `mspb` | Yes |
| `itc` | ITC Autorouter | ITC | `itc` | Yes |
| `irsplr` | IRSPLR Autorouter | IRSPLR | `irsplr` | Yes |
| `ohtax0` | OHTAX0 Autorouter | OHTAX0 | `ohtax0` | Yes |
| `mnsutb` | MNSUTB Autorouter | MNSUTB | `mnsutb` | Yes |

The `smd`/`dar` progress model also includes `counsel`; that is workflow behavior and
should not be forced into a single metadata field. A later model can represent a batch
sequence once the behavior has characterization tests.

Do not add callbacks, handler classes, row predicates, or Selenium functions to the
initial `ModeSpec`. Doing so would turn a safe metadata registry into a routing rewrite.

## Compatibility layer

The compatibility layer should make mode identity explicit without changing the
runtime call graph.

### Canonicalization

```python
def normalize_mode(mode, *, dar_mode=False) -> str:
    # Reproduce the current config fallback.
    # Unknown values initially fall back as the current callers do.
    ...
```

The exact unknown-value rule should be locked by a test before implementation.
GUI callers currently reject unknown selections, while several display/runtime
conditionals effectively fall back to SMD.

### Legacy flags

```python
@dataclass(frozen=True)
class LegacyModeFlags:
    dar_mode: bool = False
    wc_mode: bool = False
    mspb_mode: bool = False
    itc_mode: bool = False
    irsplr_mode: bool = False
    ohtax0_mode: bool = False
    mnsutb_mode: bool = False


def flags_for_mode(mode: str) -> LegacyModeFlags:
    ...


def mode_from_flags(flags: LegacyModeFlags) -> str:
    # Preserve: mspb > itc > irsplr > ohtax0 > mnsutb > dar > smd
    ...
```

Do not reject multiple true flags initially. Rejection would change behavior. Tests
may log contradictory flags, but the wrapper must retain today's precedence until a
separate cleanup is approved.

### Wrapper

The first wrapper should be deliberately thin:

```python
def run_automation_for_mode(mode: str, **workflow_kwargs):
    flags = flags_for_mode(mode)
    return run_automation_workflow(
        **workflow_kwargs,
        dar_mode=flags.dar_mode,
        wc_mode=flags.wc_mode,
        mspb_mode=flags.mspb_mode,
        itc_mode=flags.itc_mode,
        irsplr_mode=flags.irsplr_mode,
        ohtax0_mode=flags.ohtax0_mode,
        mnsutb_mode=flags.mnsutb_mode,
    )
```

Its purpose is to provide a canonical entry point while the legacy function remains
the implementation. It must not select rows, instantiate handlers, or touch a driver.

## Phased implementation

### Phase 0: Documentation and baseline

Deliverables:

- current architecture map;
- risk and behavior-invariant list;
- registry/wrapper proposal;
- inventory of repeated mode conditionals.

Exit gate: documentation review and agreement on the proposed seam.

### Phase 1: Data-only registry and unit tests

Implementation status: completed in `core/router_modes/`. The GUI mode-option list is
the only migrated consumer.

Deliverables:

- immutable registry;
- lookup and iteration helpers;
- tests for exact keys, ordering, labels, uniqueness, and document-only classification;
- no imports from Selenium, PyQt, pandas, or workflow/router modules.

Suggested first consumers after tests pass:

- GUI mode option list;
- application titles;
- notifier display names;
- workflow router labels.

Exit gate: snapshots prove user-visible strings and option ordering are unchanged.

### Phase 2: Compatibility flags and wrapper

Implementation status: completed in `core/router_modes/compatibility.py`. GUI worker
creation uses `flags_for_mode()`, and worker crash reporting uses
`mode_from_flags()`. The routing workflow retains its existing signature and direct
runtime implementation.

Deliverables:

- `LegacyModeFlags`;
- `flags_for_mode()` and `mode_from_flags()`;
- `run_automation_for_mode()` delegating to the unchanged workflow;
- precedence tests for every single mode and contradictory flag combinations;
- a wrapper delegation test using mocks, with no browser launch.

Adoption order:

1. worker crash-mode reconstruction;
2. GUI worker creation;
3. other non-Selenium callers.

Keep the old workflow signature throughout this phase.

Exit gate: old and wrapped entry points receive identical arguments and return the
same values under mocked orchestration.

### Phase 3: Orchestration policy extraction

Implementation status: completed in `core/router_modes/orchestration.py`. The workflow
now delegates mode identity, court-specific run-scope selection, batch metadata,
initial status, and parallel router labels to non-browser policy helpers. Existing row
predicates remain authoritative and are injected by the workflow.

Only after approval, move non-browser policy behind mode-aware helpers:

- run-scope filtering;
- document-only versus counsel/main batch planning;
- progress and result labels;
- notification classification.

At this stage, a separate `ModeRunContext` may carry the `ModeSpec` plus legacy flags.
`CaseLawRouter` should still receive the same values and execute the same methods.

Exit gate: characterization tests show identical selected row indices, batch order,
progress events, statuses, and notification payloads for single and parallel runs.

### Phase 4: Mode handler wrappers around existing router methods

Implementation status: completed in `core/router_modes/handlers.py` for MSPB, ITC,
IRSPLR, OHTAX0, and MNSUTB. The handlers only delegate metadata recording,
extraction, ITC postprocessing, and specialized form filling to existing
`CaseLawRouter` methods. SMD and DAR remain on the shared legacy path.

Only after a separate explicit agreement, introduce small handlers that delegate to
existing `CaseLawRouter` methods. Initial handlers should wrap, not copy, Selenium:

```text
ModeHandler
  -> classify/select metadata strategy
  -> call existing CaseLawRouter extraction method
  -> call existing CaseLawRouter form-fill method
```

The first implementation must keep selectors and browser operations in their current
methods. This phase creates ownership boundaries without changing those operations.

Exit gate: mocked WebDriver call traces and status transitions match the baseline.

### Phase 5: Optional Selenium extraction

Implementation status: all five specialized document form-routing flows—OHTAX0,
MNSUTB, MSPB, IRSPLR, and ITC—and the shared SMD/DAR fallback are extracted. Their
`CaseLawRouter` entry points and specialized dispatch precedence remain compatible.
Navigation and most recovery UI remain on the router. Common docket/date/page/court
preparation, final route/Ready/Save handling, SMD/DAR counsel comments/LNI linkage,
main-opinion field composition, and related-LNI discovery/attachment now delegate
through compatibility wrappers to `common_fields_selenium.py`,
`routing_save_selenium.py`, `counsel_fields_selenium.py`,
`main_opinion_fields_selenium.py`, and `related_lni_selenium.py`. Pending-alert
acceptance and duplicate classification additionally delegate to
`alert_recovery_selenium.py`; tab cleanup/focus policies delegate to
`tab_lifecycle_selenium.py`. Browser-session-loss classification, exception
translation, and remaining-row status propagation delegate to the non-browser
`session_loss_policy.py`. Modify-mode entry and its alert/retry policy delegate to
`modify_recovery_selenium.py`. Search Inventory readiness and refresh/menu recovery
delegate to `search_inventory_recovery_selenium.py`. LNI field submission, Search
clicking, result-availability checks, and retry orchestration delegate to
`lni_search_selenium.py`. Result availability, multi-strategy result selection, and
popup/tab tracking delegate to `result_navigation_selenium.py`. Modify entry,
form-fill delegation, cleanup, and fresh-start retry orchestration delegate to the
selector-free `form_opening_selenium.py`. Duplicate policy, popup handling,
archive/process selection, Continue, overlay-clear checks, and diagnostics delegate
to `duplicate_overlay_selenium.py`. Ready clicking, post-click alerts, overlay
classification, and the legacy duplicate-save path delegate to
`ready_postclick_selenium.py`. See the extraction documents for preserved contracts
and validation limits.

Continue one mode at a time, keep the public router method available for compatibility,
and verify each extraction against controlled fixtures or a staging environment.

## Test strategy before Selenium refactoring

### Pure unit tests

- registry contents and ordering;
- canonical mode-to-flag mapping;
- legacy flag-to-mode precedence;
- filename detection fixtures;
- row predicates and run-scope selection;
- extractor parsing with stored text/PDF fixtures;
- label and notification mapping.

### Characterization tests with mocks

- workflow delegates the same flags to `CaseLawRouter.process_rows()`;
- each mode produces the same batch names and callback order;
- parallel and single-router planners select the same row indices;
- exceptions reconstruct the same mode and notification payload;
- wrapper forwards all callbacks and data objects without alteration.

### Selenium contract tests

Before moving browser code, capture for each mode:

- search and result-selection sequence;
- selected form filler;
- fields written and route label selected;
- duplicate policy;
- status transitions;
- retry and cleanup calls.

These should use a fake/recording driver where possible. A small staging smoke test
should be reserved for the point where browser code actually changes.

## Explicit non-goals for the first two phases

- no Selenium selector or timeout changes;
- no rewrite of `CaseLawRouter.process_batch()` or `process_rows()`;
- no extractor behavior changes;
- no filename-pattern consolidation;
- no removal of `dar_mode` or `wc_mode` compatibility parameters;
- no status-string cleanup;
- no correction of visible labels;
- no change to parallel routing;
- no edits to the production backup project.

## Recommended next approval

Review the six extracted form-routing boundaries, the fifteen helper boundaries,
the batch architecture review, and the documented lack of live staging validation.
Phases 6A through 6E are complete: Ready/post-click extraction, batch
characterization, pure batch policy, and all five specialized document-row wrappers.
Phase 6F document-only run dispatch and the first Phase 6G shared SMD/DAR
counsel/defer/window-cleanup/main slice are complete. The second Phase 6G slice moves
shared success state and optional error-report output behind a separate wrapper.
The third Phase 6G slice centralizes repeated progress callback policy without
moving its outer-loop call sites.
The fourth Phase 6G slice extracts post-loop throughput calculation and exact
summary logging while retaining clock placement and counters in the router.
The fifth Phase 6G slice extracts row-level router-session-loss side effects into the
existing non-Selenium policy while retaining stop/break control in the router.
The sixth Phase 6G slice extracts generic row-error recording while leaving driver
cleanup and `finally` control in the router.
The seventh Phase 6G slice extracts completed/invalid/processable row preflight while
leaving `continue`, timing, dispatch, and browser behavior in the router.
The eighth Phase 6G slice extracts post-form status/duration outcomes and timing-log
formatting while leaving retry and counter mutation in the router.
`process_batch()` remains the outer-loop runtime implementation; `process_rows()`
retains filtering, dispatch, returns, and its broad exception boundary. The Phase 6G
checkpoint recommends no further Phase 6G code movement. The next optional gate is
Phase 7A characterization only for the document-wrapper outcome block;
Selenium-adjacent extraction remains separately gated.

Phase 7A is now complete with eight dedicated call-site tests and no production
source change. Phase 7B subsequently extracted the approved selector-free
document-outcome dispatcher. Its architecture checkpoint is complete and recommends
characterization-only Phase 8A for the shared-search/form-transition call site.
Phase 8A is now complete with eight no-driver tests and no production source change.
Phase 8B subsequently extracted the approved selector-free shared-search/form
transition. Status application, finalization, exceptions, progress, counters, and
driver cleanup remain in the router. The post-Phase 8B checkpoint concludes that no
further batch-code movement is needed for mode readability. The next recommended
phase is a documentation-only developer mode-integration guide.

Phase 9A is now complete in `MODE_DEVELOPER_INTEGRATION_GUIDE.md`. It documents the
actual hybrid registry/legacy-flag architecture, the explicit five-slot metadata
schema, safe delivery gates, required test layers, staging decisions, and MNSUTB
compliance.
