# Router Mode Developer Integration Guide

Status: Phase 9A complete; documentation only  
Audience: developers adding or changing SADM Autorouter modes  
Scope: `SADM Autorouter Sandbox`

Documentation entry point: [README.md](README.md)  
Current closeout: [MODULARIZATION_CLOSEOUT.md](MODULARIZATION_CLOSEOUT.md)

## Safety rule

Develop and validate mode changes only in `SADM Autorouter Sandbox`. The sibling
`SADM Autorouter` folder is the stable production backup and must not be edited.

Do not perform live routing, workbook mutation, or staging browser validation unless
that action is explicitly authorized for the phase.

## What the mode registry is—and is not

`core/router_modes/registry.py` is the source of truth for stable mode identity and
presentation metadata. It controls:

- canonical key;
- GUI display name and ordering;
- router label;
- progress batch label;
- result label;
- document-only classification.

The registry is intentionally data-only. It does not make the application a dynamic
plug-in system.

A genuinely new document mode still requires explicit integration with legacy
boolean flags, workflow signatures, scope selection, batch policy, handler
precedence, metadata slots, row processing, form dispatch, reporting, and tests.
Adding only a `ModeSpec` creates an incomplete mode.

## Current execution path

```text
GUI registry choice
  -> canonical key
  -> LegacyModeFlags
  -> workflow run plan and row scope
  -> document-only run dispatch
  -> process_batch outer loop
  -> document-row outcome dispatcher
  -> mode batch-row wrapper
  -> batch form-transition wrapper
  -> form handler
  -> mode Selenium compatibility wrapper
  -> status/metadata/error reporting
```

The 146-line `CaseLawRouter.process_batch()` is the visible lifecycle controller. It
should not absorb new mode implementations.

## Existing document-mode matrix

| Mode | Row scope | Batch-row module | Form module | Missing metadata | Special behavior |
| --- | --- | --- | --- | --- | --- |
| MSPB | Full/filtered legacy main set; explicit flag | `mspb_batch_row.py` | `mspb_selenium.py` | Skip | No row predicate; flag has highest row precedence |
| ITC | `is_itc_row()` | `itc_batch_row.py` | `itc_selenium.py` | Skip | Row-aware; duplicate fingerprint postprocessing; no `process_batch` flag |
| IRSPLR | `is_irsplr_row()` | `irsplr_batch_row.py` | `irsplr_selenium.py` | Fallback | May archive excluded/unreadable cases |
| OHTAX0 | `is_ohtax0_row()` | `ohtax0_batch_row.py` | `ohtax0_selenium.py` | Skip | Court/filename-aware |
| MNSUTB | `is_mnsutb_row()` | `mnsutb_batch_row.py` | `mnsutb_selenium.py` | Skip | Source Detail must be `Table-(5-day spec source)` |

SMD and DAR use the shared counsel/main path and
`core/router_modes/smd_dar_selenium.py`; they are not document handlers.

## Choose the change type first

### Presentation-only change

Examples: display label or result label.

Start in `registry.py`. Verify GUI, notifier, and registry tests. Do not change
runtime policy unless the business behavior also changes.

### Existing-mode policy or parsing change

Examples: new court code, filename recognition, missing-metadata policy, or Source
Detail rule.

Change the smallest authoritative extractor or policy module. Treat a compliance
value change as a business-behavior change, not as refactoring. Add a dedicated
compliance test when the exact value is mandatory.

### New document mode

Follow every integration step below. Plan the work in small gates, with
characterization before Selenium movement.

### New shared counsel/main mode

Do not copy the document-mode recipe blindly. SMD/DAR use shared filtering,
counsel/main sequencing, related-LNI behavior, and shared form filling. Start with a
separate architecture review.

## New document-mode integration sequence

### 1. Define identity

Update `core/router_modes/registry.py`:

- add one immutable `ModeSpec`;
- choose the stable GUI position deliberately;
- set `document_only=True`;
- define exact display, router, progress, and result labels.

Update registry tests to lock ordering, uniqueness, immutability, and
document-only membership.

### 2. Extend legacy compatibility

Update `core/router_modes/compatibility.py`:

- add the boolean field to `LegacyModeFlags`;
- add it to `LEGACY_MODE_PRECEDENCE` at the approved position;
- emit it from `flags_for_mode()`;
- preserve unknown-mode fallback to SMD;
- preserve `wc_mode` compatibility even if the new mode does not use it.

Then trace the flag through:

- `frontend/pyqt_threading.py` constructor, stored state, workflow call, and crash
  mode identification;
- `core/smducar_workflow.py` public and parallel workflow signatures and calls;
- `CaseLawRouter.process_rows()` and `dispatch_document_run()` signatures;
- any notifier or result-count helper that still receives explicit mode flags.

Precedence is behavior. Never append a flag without defining how contradictory flags
resolve in identity, scope, row dispatch, form dispatch, and document-run dispatch.

### 3. Define run plan and scope

Update `core/router_modes/orchestration.py`:

- `BATCH_TYPES`;
- `INITIAL_STATUS`;
- `SCOPE_FLAG_PRECEDENCE` when the mode filters rows;
- `EMPTY_SCOPE_MESSAGES`;
- the row-predicate mapping supplied by `run_automation_workflow()`.

Create an authoritative pure row predicate in the mode extractor. Prefer court-code
and filename helpers plus a single `is_<mode>_row(row)` entry point.

MSPB is the existing exception: it does not use a court-specific scope predicate.
Do not reproduce that exception accidentally.

### 4. Define document batch policy

Update `core/router_modes/batch_policy.py`:

- add the batch type to `SUPPORTED_PROGRESS_BATCHES`;
- add a `DocumentBatchPolicy`;
- choose exact started and processed statuses;
- decide whether the mode uses `filtered_main` or the full input;
- define `process_batch_flag`, or explicitly use `None` for a row-aware path;
- add a `MissingMetadataPolicy`.

Missing metadata must have an explicit action:

- `skip`, with an exact terminal row status; or
- `fallback`, with a documented metadata construction rule.

Also update `DOCUMENT_MODE_FLAG_PRECEDENCE` in
`document_run_dispatch.py`.

### 5. Build the pure extractor contract

Create `core/<mode>_extractor.py` without Selenium imports.

The established immutable metadata shape starts with:

```python
@dataclass(frozen=True)
class ExampleMetadata:
    court: str
    docket_number: str
    decision_date: str
    source_detail: str
    other_numbers: tuple[str, ...] = ()
    comments_text: str = ""
    title_hint: str = ""
```

Add only mode-required fields, such as exclusion or duplicate indicators. Provide:

- court-code and filename recognition helpers;
- `is_<mode>_row(row)` when scope or row dispatch needs it;
- `parse_<mode>_document_text(...)`;
- `parse_<mode>_pdf_bytes(...)`;
- deterministic handling for empty, malformed, and image-only input;
- exact business constants for controlled values.

Parsing and classification tests should not need a driver.

### 6. Add router compatibility methods

The handler is a method-name adapter, so the router must expose stable compatibility
methods for:

- metadata recording;
- metadata extraction from the selected search result;
- form filling;
- optional metadata postprocessing;
- the document-row wrapper.

Keep these router methods thin. New implementation logic belongs in extractor,
batch-row, or Selenium modules.

Metadata reporting currently shares `mspb_metadata_buffer`. A new recorder must set
an unambiguous `Metadata Type` and preserve the existing report column contract.
Mode-specific buffers require a separate reporting design review.

### 7. Register the handler and precedence

Add a `DocumentModeHandler` in `core/router_modes/handlers.py` with exact method
names and its metadata keyword.

Update both selectors:

- `select_row_mode_handler()` for row precedence;
- `select_form_mode_handler()` for metadata/form precedence.

These precedence orders are currently explicit conditionals. Add contradictory-signal
tests. Do not assume dictionary insertion order is the business rule.

### 8. Add the document-row wrapper

Create `core/router_modes/<mode>_batch_row.py`.

Follow the established outcome contract:

- record metadata attempt;
- perform the existing search/navigation sequence;
- extract and optionally postprocess metadata;
- apply the missing-metadata policy;
- record extracted, fallback, failed, or excluded metadata state;
- return an immutable outcome containing metadata, `continue_to_form`, and
  `row_status`.

Do not write outer-loop counters, progress, or driver cleanup here.

Update `document_row_outcome_dispatch.py` to:

- pass the new flag and row predicate;
- invoke the new compatibility wrapper;
- populate exactly the new mode’s metadata slot;
- preserve unknown-handler shared fallback;
- preserve eager predicate evaluation unless a separately approved behavior change
  says otherwise.

### 9. Expand the explicit metadata-slot schema

The current form pipeline has exactly five document metadata slots:

```text
mspb_metadata
itc_metadata
irsplr_metadata
ohtax0_metadata
mnsutb_metadata
```

A sixth document mode requires coordinated schema changes in:

- `DocumentRowOutcome`;
- `dispatch_document_row_outcome()`;
- `process_batch_form_transition()` form keyword construction;
- `CaseLawRouter.open_and_process_form()`;
- form-opening compatibility calls;
- `CaseLawRouter.fill_irt_form()`;
- its `metadata_by_mode` mapping;
- retry forwarding;
- call-site and direct tests that assert exact slots.

Do not reuse another mode’s slot or hide metadata in a generic object without a
separately reviewed migration plan.

### 10. Implement form dispatch and Selenium behavior

Create `core/router_modes/<mode>_selenium.py`. Keep the router’s
`fill_<mode>_irt_form()` as a thin compatibility entry point.

Before implementation, characterize:

- field order;
- selectors and waits;
- exclusion/archive behavior;
- duplicate handling;
- Ready/Save order;
- returned status strings;
- cleanup and exception propagation.

Reuse shared wrappers for common fields, routing/save, alerts, tab lifecycle, and
Ready/post-click behavior. Do not copy shared Selenium state machines into the new
mode module.

Any selector, wait, click order, route, save, tab, or alert change requires explicit
browser-adjacent approval. Decide and document whether a controlled staging smoke
test is required before running one.

### 11. Integrate reporting and completion behavior

Verify:

- row statuses and rerun eligibility;
- `mspb_metadata_buffer` record fields and `Metadata Type`;
- error-log mode classification;
- Excel metadata report columns and flush behavior;
- processed-count and duration semantics;
- progress batch recognition;
- success/error messages;
- single-router and parallel-router result counts;
- critical-error and run-summary mode labels.

Status spelling and capitalization are external contracts because workbooks,
rerun logic, tests, and operators consume them.

## Required test layers

For a new document mode, add or update all applicable layers:

1. registry identity/order tests;
2. canonical/legacy flag and precedence tests;
3. run-plan, scope, empty-scope, and workflow integration tests;
4. pure extractor and business-compliance tests;
5. handler method-name and row/form precedence tests;
6. batch policy and document-run dispatch tests;
7. isolated `<mode>_batch_row` tests;
8. isolated `<mode>_selenium` characterization tests;
9. document-row outcome direct and call-site tests;
10. batch form-transition direct and call-site tests;
11. `process_batch()` and `process_rows()` characterization;
12. full offline discovery:

```powershell
python -B -m unittest discover -s tests
```

Use `python -B` so validation does not create bytecode artifacts in the workspace.
Expected warning/error logs from deliberate failure tests are acceptable; a nonzero
test exit is not.

## Safe phased delivery template

Use separate approvals for these gates:

1. documentation and pure registry/policy contracts;
2. extractor and predicate implementation;
3. handler and batch-row outcome integration;
4. Selenium characterization only;
5. Selenium implementation;
6. call-site and full regression verification;
7. optional staging smoke, only when explicitly authorized;
8. architecture checkpoint.

Do not combine a business-rule change with a structural extraction unless the phase
explicitly authorizes both.

## Definition of done

A mode is integrated only when:

- every identity, scope, precedence, status, and metadata decision is explicit;
- the GUI can select it and the worker/workflow preserve its identity;
- single and parallel execution choose the intended rows;
- document and form dispatch select only that mode under its approved precedence;
- all early, success, failure, retry, and session-loss outcomes are characterized;
- reporting and rerun behavior are verified;
- exact compliance values have dedicated tests;
- the full offline suite passes;
- staging status is recorded;
- the production backup remains untouched.

## MNSUTB compliance example

MNSUTB demonstrates how to treat a controlled business value:

- authority: `core/mnsutb_extractor.py`;
- constant: `MNSUTB_SOURCE_DETAIL`;
- required value: `Table-(5-day spec source)`;
- focused protection: `tests/test_mnsutb_source_detail_compliance.py`;
- downstream form characterization:
  `tests/test_mnsutb_selenium_characterization.py`.

Do not replace this value with `Order` during refactoring or test-fixture cleanup.
