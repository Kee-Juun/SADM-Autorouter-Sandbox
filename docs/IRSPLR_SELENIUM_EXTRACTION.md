# IRSPLR Selenium Extraction

Status: fourth Phase 5 slice implemented  
Scope: IRSPLR IRT form-routing flow only

## New boundary

`core/router_modes/irsplr_selenium.py` owns the IRSPLR form-routing sequence formerly
implemented by `CaseLawRouter.fill_irsplr_irt_form()`.

The router method retains its signature as a compatibility entry point. Shared field
filling, locked-Archive detection, dropdown helpers, already-processed inspection,
browser cleanup, metadata acquisition, and PDF parsing remain on the router or in the
extractor.

## Preserved branch contract

No-driver tests passed against both implementations and lock:

- missing-metadata skip behavior;
- unreadable-text fallback when the form is already processed;
- unreadable-text `SKIPPED: IRSPLR OCR REQUIRED` behavior otherwise;
- locked Excluded/Archive forms as `ALREADY PROCESSED`;
- normal documents selecting `Outside Conversion`;
- excluded documents selecting `Archive`;
- disabled excluded routes already confirmed as `Archive`;
- common-field, alert, Ready to Process, and final save arguments.

The full suite passed 50 tests at extraction.

## Live validation not performed

No authenticated staging or production route was executed. Controlled validation
requires safe normal, excluded, unreadable, and already-processed IRSPLR staging
records plus explicit authorization to modify their external state.

Recommended checks:

1. verify normal `Outside Conversion`;
2. verify enabled and disabled Excluded/Archive cases;
3. verify unreadable-PDF handling for processed and unprocessed forms;
4. verify output court, docket, date, source detail, comments, Ready, and save;
5. compare workbook status, logs, and external state with the branch contract.

## Next gate

ITC was subsequently characterized and extracted after separate approval. Its true
duplicate, excluded, locked Archive, disabled-route, and temporary duplicate-policy
contracts are recorded in `ITC_SELENIUM_EXTRACTION.md`.
