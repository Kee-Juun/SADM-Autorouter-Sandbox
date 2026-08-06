# Production Change Sync — 2026-08-07

Status: complete
Source: sibling `SADM Autorouter` project, inspected read-only
Target: modular `SADM Autorouter Sandbox`

## Scope and architectural decision

The production and sandbox trees were compared by source hash and modification time.
Only changes newer than the 2026-07-28 sync were considered. The production
`smducar_router.py` remains a monolithic counterpart to behavior already extracted
behind the sandbox's registry and `core/router_modes/` wrappers, so it was not copied.

The applicable changes were integrated at existing shared-service boundaries:

- driver discovery in `core/chromedriver_resolver.py`;
- MSPB parsing in `core/mspb_extractor.py`;
- run reporting in `core/critical_error_notifier.py`.

No registry entries, mode flags, handler precedence, Selenium selectors, routing
order, Ready/Save behavior, or batch orchestration boundaries changed.

## Ported changes

### Offline-capable ChromeDriver reuse

Before using `webdriver_manager`, the resolver now searches for an existing driver:

- beside a frozen PyInstaller application;
- in supported project-relative driver locations;
- in the `.wdm` ChromeDriver cache, newest first.

An existing driver is used only when its major version matches installed Chrome.
An incompatible candidate falls through to the existing download and validation
flow. The final error now explains both connectivity and cached/bundled fallback.

Tests mock all candidates, versions, and downloads. Validation did not launch Chrome,
access the network, alter the driver cache, or execute a real driver binary.

### MSPB title-driven Source Detail

MSPB parsing now finds title lines that begin with a supported title even when more
text follows, such as `FINAL ORDER DISMISSING THE PETITION`. The detected title hint
is passed into Source Detail classification:

- `INITIAL DECISION` remains `Opinion` through its court classification;
- titles containing `OPINION`, or starting with `DECISION`, resolve to `Opinion`;
- titles containing `ORDER` resolve to `Order`;
- existing court-specific precedence remains unchanged.

This parser change is automatically consumed by the modular MSPB batch-row and
Selenium wrappers through the existing metadata object; no router method duplication
was introduced.

### Notification subjects and troubleshooting

Critical and success notifications now include:

- `SADM Autorouter: MODE - message - MM/DD/YYYY HH:MM:SS AM/PM` subjects;
- expanded randomized message themes;
- rerun-row previews accepting either `Excel Row` or `Row` keys;
- issue-specific troubleshooting for reset, session loss, Search Inventory, Modify,
  unreadable PDF/OCR, related-LNI, and general rerun cases.

These changes remain inside the shared notifier and do not affect routing decisions.

## Deliberately not copied

- the production monolithic `core/smducar_router.py`;
- older production workflow, worker, and GUI branches that predate the sandbox mode
  registry;
- runtime configuration or selected mode;
- any production build/output artifacts.

The sibling production project was not modified.

## Verification

- new and expanded focused contracts: 15 tests passing;
- affected resolver/MSPB/registry/batch set: 52 tests passing;
- full offline suite: 381 tests passing, zero failures and zero errors.

No browser, staging route, external routing action, network download, driver-cache
deletion, workbook mutation, email send, or production-project write was performed.
