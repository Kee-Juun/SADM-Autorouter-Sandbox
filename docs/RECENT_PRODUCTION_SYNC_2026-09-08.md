# Production Sync — September 8, 2026

Status: implemented and covered by offline regression tests  
Source: read-only `SADM Autorouter` production checkout  
Target: modular `SADM Autorouter Sandbox`

## Production changes mapped into the sandbox

This sync adapts production commits `275668c`, `3890f35`, and `ef7b765` without
replacing the sandbox's modular routing architecture.

- Route errors (`ROUTE ERROR`, `ROUTE_ERROR`, and `ROUTE DROPDOWN ERROR`) now
  participate in the existing refresh-and-retry policy.
- Batch success totals count only rows ending as `DONE`. Other terminal or error
  results remain visible but are not reported as newly routed documents.
- Per-row and throughput logs now distinguish successful routing from completion
  without a successful save.
- Main-opinion Case Name preserves an existing value and fills `RE` only when the
  field is blank and interactable.
- Route-selection failures include the original exception in their logs.
- ITC may use the filename docket when readable text clearly belongs to ITC but has
  no primary docket. Conflicting loose docket numbers and non-ITC text block that
  fallback.
- MOSU is registered as a hybrid mode: counsel and ordinary main PDFs use the shared
  SMD flow, while minutes HTML rows use specialized table-case routing.

## Modular placement

- `core/itc_extractor.py` contains the production parser and strict fallback rules.
- `core/mosu00_extractor.py` owns MOSU filename/row detection and HTML parsing.
- `core/router_modes/mosu00_batch_row.py` owns table-row preparation and missing
  metadata policy.
- `core/router_modes/mosu00_router_mixin.py` isolates MOSU metadata acquisition and
  Selenium table-dialog behavior from `CaseLawRouter`.
- The existing registry, compatibility, orchestration, outcome dispatch, form
  transition, worker, and GUI boundaries carry the new mode without duplicating the
  production monolith.

## Business-compliance lock

MOSU table cases and MNSUTB documents both use the exact controlled Source Detail:

`Table-(5-day spec source)`

The value is asserted by regression tests and must not be shortened to `Order`.

## Validation

- Python compilation: passed.
- Focused ITC/MOSU sync tests: passed.
- Full offline suite baseline: 391 tests.

Live Selenium routing remains a separate staging validation step because it changes
external IRT state.
