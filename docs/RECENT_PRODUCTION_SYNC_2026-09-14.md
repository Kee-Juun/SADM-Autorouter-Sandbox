# Production Sync — 2026-09-14

Source reviewed: production commit `c78d3b9` (`Add MEWORK routing and expand progression system`).

The production folder was inspected read-only. Its local `config/config.json` mode
selection was intentionally not copied into the sandbox.

## Changes carried into the sandbox

- MEWORK (`STMEWORK`) detection, PDF parsing, duplicate fingerprinting, IRT routing,
  statuses, summaries, notifications, and packaging support.
- ITC miscellaneous docket parsing and its production regression tests.
- Expanded rewards/progression rules, failed-run recovery tracking, duration-aware
  rewards, badge effects, generators, and the new achievement artwork.
- Production critical-error, rerun-status, shared utility, GUI, and application-name
  updates.

## Modular adaptation

MEWORK was not copied into the shared router as one monolithic block. It is registered
in `core/router_modes/registry.py` and travels through the existing compatibility,
scope, policy, document dispatch, metadata outcome, form-transition, worker, workflow,
and GUI boundaries. Its row orchestration lives in `mework_batch_row.py`; PDF/browser
metadata acquisition lives in `mework_router_mixin.py`; pure parsing remains in
`core/mework_extractor.py`. The existing ITC-style form flow is reused with a MEWORK
context label.

Inactive modes retain their previous call shapes where practical, so adding MEWORK
does not force unrelated Selenium paths to receive a new keyword argument.

## Compliance and validation

The controlled MNSUTB Source Detail remains exactly
`Table-(5-day spec source)`. It was not replaced with `Order` or any production-local
preference.

- Python AST validation: 136 files passed.
- Full offline regression suite: 419 tests passed.
- No live IRT/Selenium routing was performed.
- No executable was rebuilt in this sync.

