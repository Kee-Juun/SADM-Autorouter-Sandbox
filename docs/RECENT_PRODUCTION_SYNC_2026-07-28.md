# Original-Project Change Sync — 2026-07-28

Status: complete  
Source: sibling `SADM Autorouter` project, inspected read-only  
Target: `SADM Autorouter Sandbox`

## Ported changes

### OHTAX0 extraction

`core/ohtax0_extractor.py` now matches the original project’s recent parser:

- CASE NO(S). continuation scanning expands from 3 to 34 following lines;
- title scanning expands from 8 to 35 lines;
- title scanning stops at `APPEARANCES` or `ENTERED`;
- numeric case-number continuation lines are ignored while searching for the title.

Focused tests cover a twelve-number header and the APPEARANCES boundary.

### Canonical Table Source Detail

The exact compliant value `Table-(5-day spec source)` is now used by:

- `MNSUTB_SOURCE_DETAIL`;
- `core.smducar_excel.get_source_detail_mapping()["t"]`;
- `frontend.pyqt_utils.extract_source_detail_from_filename()` for `t`/`table`.

The MNSUTB compliance suite now locks the extractor, form field, Excel mapping, and
filename mapping.

### ChromeDriver resolution

Added `core/chromedriver_resolver.py` and integrated it with:

- `core/smducar_workflow.py`;
- `core/smducar_selenium.py`.

The resolver:

- detects installed Chrome version from the Windows registry or executable;
- requests that version from `webdriver_manager`;
- locates the real `chromedriver.exe`;
- reads and compares Chrome/driver major versions;
- clears only the validated `.wdm/drivers/chromedriver` cache after a detected
  mismatch;
- retries default manager detection;
- raises an actionable error if no compatible driver resolves.

All resolver tests are mocked. No driver download, Chrome launch, network request,
or cache deletion occurred during this sync.

### Build specification

Added `SADM Autorouter Plus+.spec`, matching the original project’s new Plus+ build
configuration.

## Deliberately not copied

- `config/config.json` mode changed from `mspb` to `ohtax0` in the original. This is
  local runtime selection state, not source behavior.
- The original router, workflow, GUI mode list, and worker error-mode branches were
  not copied wholesale because they predate the Sandbox registry and modularization.
- Existing Sandbox registry, compatibility, orchestration, wrappers, tests, and
  documentation remain authoritative.

## Verification

- new/expanded focused contracts: 13 tests passing;
- affected OHTAX0/workflow/Selenium set: 26 tests passing;
- full offline suite: 373 tests passing.

Expected mismatch/download warnings are deliberate mocked failure-path tests.

No live browser, staging route, external routing action, workbook write, or
production-project write was performed.
