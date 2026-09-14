# Router Mode Modularization Closeout

Status: Phase 9B complete; documentation closeout  
Scope: behavior-preserving mode modularization through Phase 9A

## Outcome

The original goal is complete:

- current architecture was inspected and documented;
- stable mode identity is centralized in an immutable registry;
- canonical keys translate through preserved legacy flags;
- run planning and row scope are explicit non-browser policy;
- specialized document handlers are registered adapters;
- document-mode form flows and the shared SMD/DAR flow have module boundaries;
- shared Selenium state machines have focused compatibility wrappers;
- document-only and shared run orchestration have explicit outcomes;
- batch preflight, finalization, errors, session loss, progress, and throughput have
  isolated policy boundaries;
- document-row selection/outcomes and shared-search/form transitions have immutable
  wrappers;
- `process_batch()` is a readable outer-loop controller;
- a developer mode-integration guide documents the real extension path.

No further batch-code movement is recommended for readability alone.

## Current architecture baseline

| Item | Current value |
| --- | ---: |
| `core/smducar_router.py` | 3,590 lines |
| `CaseLawRouter.process_batch()` | 178 lines |
| `CaseLawRouter.process_rows()` | 65 lines |
| Router class methods | 159 |
| `core/router_modes/` Python modules | 45 |
| Full offline suite | 419 tests |

The remaining router size does not indicate that every method should move. It
contains compatibility entry points plus shared browser/PDF helpers whose extraction
would require separate value and risk analysis.

## Stable ownership boundaries

### Registry and pure policy

`core/router_modes/` owns mode identity, legacy compatibility, run plans, scope,
batch policy, handlers, immutable outcomes, and extracted orchestration policies.
Pure modules avoid importing Selenium and the router where their contracts require
isolation.

### Mode parsing

`core/*_extractor.py` owns document parsing, row recognition, classification, and
controlled metadata values.

### Browser implementation

`core/router_modes/*_selenium.py` owns extracted mode and shared Selenium flows.
`CaseLawRouter` retains thin compatibility methods and remaining shared browser
utilities.

### Outer lifecycle

`CaseLawRouter.process_batch()` owns iteration, outcome application, counters,
exception selection, progress, stop/break control, throughput gating, and returned
totals.

`CaseLawRouter.process_rows()` owns filtering, high-level run dispatch, finalization,
returns, and its broad exception boundary.

## Deliberately retained compatibility

The system remains hybrid rather than dynamically pluggable:

- public workflow and worker APIs still accept legacy boolean flags;
- precedence tables and explicit conditionals remain behavior contracts;
- five document metadata slots are explicit across outcomes and form signatures;
- reporting shares `mspb_metadata_buffer` with a `Metadata Type` discriminator;
- router compatibility methods preserve existing call sites and patch points.

The developer guide explains every required integration point for a new mode.

## Validation record

The current offline baseline is 384 passing tests. It covers:

- registry, compatibility, orchestration, and workflow policy;
- all five document batch-row wrappers;
- all five specialized and shared SMD/DAR form modules;
- shared Selenium helper boundaries;
- document outcome and form-transition direct/call-site behavior;
- `process_batch()` and `process_rows()` lifecycle;
- session loss, retry, duplicate, tab, alert, routing/save, and error paths;
- MNSUTB Source Detail compliance.

Expected warning/error logs are deliberate test fixtures.

## Live-validation record

No live browser, staging route, external routing action, or workbook write was
performed during this closeout. Phase 7B and Phase 8B wrappers invoke
browser-adjacent compatibility methods but were verified offline only.

Future Selenium changes must explicitly decide whether controlled staging validation
is required. This document does not authorize it.

## Business compliance

MNSUTB Source Detail must remain exactly:

```text
Table-(5-day spec source)
```

The authoritative constant is `MNSUTB_SOURCE_DETAIL` in
`core/mnsutb_extractor.py`. `Order` is noncompliant for this mode.

## Work that requires a new approval

The following are outside the completed behavior-preserving scope:

- changing legacy flag or handler precedence;
- replacing explicit metadata slots with a generic schema;
- changing status strings or rerun semantics;
- altering selectors, waits, click order, routes, Ready/Save, tabs, or alerts;
- changing duplicate archive/process policy;
- changing driver-cleanup behavior;
- changing swallowed exception behavior;
- adding a new mode;
- performing staging or live routing;
- copying changes into the production backup.

Each should begin with a focused design/characterization phase.

## Developer handoff

For routine maintenance:

1. start at `docs/README.md`;
2. use `MODE_DEVELOPER_INTEGRATION_GUIDE.md` for mode work;
3. consult `ROUTER_MODES_ARCHITECTURE.md` for ownership;
4. consult `BATCH_ORCHESTRATION_CHARACTERIZATION.md` before lifecycle changes;
5. protect exact compliance values with focused tests;
6. run the full offline suite with `python -B`;
7. record whether staging was performed;
8. never edit the sibling production backup.

Historical phase documents remain in `docs/` as review evidence.

## Post-closeout maintenance sync

The selective 2026-07-28 original-project sync adds OHTAX0 long-header parsing,
canonical Table Source Detail mappings, compatible ChromeDriver resolution, the
Plus+ build spec, and ten additional tests without undoing modularization. See
`RECENT_PRODUCTION_SYNC_2026-07-28.md`.

The selective 2026-08-07 sync adds cached/bundled ChromeDriver reuse, improved MSPB
title-driven Source Detail classification, and richer critical/success notification
formatting at shared service boundaries. Router mode wrappers and registry ownership
remain unchanged. See `RECENT_PRODUCTION_SYNC_2026-08-07.md`.

The selective 2026-08-16 sync changes only completion-summary presentation order:
newly routed counts now appear before already-processed counts, followed by timeout
details. It adds three offline GUI-summary contracts without changing any registry,
mode, batch, or Selenium boundary. See `RECENT_PRODUCTION_SYNC_2026-08-16.md`.
