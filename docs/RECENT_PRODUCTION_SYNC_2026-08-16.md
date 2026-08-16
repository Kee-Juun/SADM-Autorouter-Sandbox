# Production Change Sync — 2026-08-16

Status: complete
Source: sibling `SADM Autorouter` project, inspected read-only
Target: modular `SADM Autorouter Sandbox`

## Change found

The parent project contains one new source change after the 2026-08-07 sync. Its
completion summary now presents results in this order:

1. successfully auto-routed counts, when any new routes completed;
2. already-processed counts;
3. timeout details, when present;
4. the existing contextual closing message.

The ordering applies to MSPB, ITC, IRSPLR, OHTAX0, MNSUTB, DAR, and SMD modes.
Zero-success runs continue to omit the successful-routing section.

## Modular integration

The behavior belongs to `SMDUSAPGui.get_success_message()` in
`frontend/smducar_pyqt.py`. The sandbox has the same GUI presentation boundary, so
the change was applied there directly. It did not require changes to:

- `core/smducar_router.py`;
- `core/router_modes/`;
- the mode registry or compatibility flags;
- batch orchestration;
- Selenium selectors, waits, routing, Ready, or Save behavior.

The parent `config/config.json` difference remains local runtime state and was not
copied.

## Verification

- focused completion-summary contracts: 3 tests passing;
- all seven mode labels covered by ordering assertions;
- timeout placement and zero-new-routing behavior covered;
- full offline suite: 384 tests passing, zero failures and zero errors.

No GUI window, browser, staging route, workbook mutation, email send, or parent
project write was performed.
