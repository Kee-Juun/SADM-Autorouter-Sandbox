# ITC Selenium Extraction

Status: fifth Phase 5 slice implemented  
Scope: ITC IRT form-routing flow only

## New boundary

`core/router_modes/itc_selenium.py` owns the ITC form-routing sequence formerly
implemented by `CaseLawRouter.fill_itc_irt_form()`.

The router method retains its signature as a compatibility entry point. Shared field
filling, ITC-specific field helpers, locked-Archive detection, dropdown helpers,
browser cleanup, metadata acquisition, PDF parsing, and duplicate classification
remain on the router or in the extractor.

## Preserved branch contract

No-driver tests passed against both implementations and lock:

- missing-metadata skip behavior;
- locked excluded/Archive forms as `ALREADY PROCESSED`;
- normal documents selecting `Outside Conversion`;
- true duplicates and excluded documents selecting `Archive`;
- disabled excluded routes already confirmed as `Archive`;
- disabled nonexcluded routes as `ALREADY PROCESSED`;
- common-field, alert, Ready to Process, and final save arguments;
- temporary `_archive_duplicate_mode` values during ITC field/save handling;
- restoration of the router's prior duplicate policy after skip, success, or error.

The extraction does not alter ITC metadata parsing or duplicate detection. The full
suite passed 59 tests after extraction and structural boundary checks.

## Live validation not performed

No authenticated staging or production route was executed. Controlled validation
requires safe normal, true-duplicate, excluded, locked-Archive, and already-processed
ITC staging records plus explicit authorization to modify their external state.

Recommended checks:

1. verify normal `Outside Conversion`;
2. verify true-duplicate and excluded `Archive` routes;
3. verify locked and disabled Archive handling;
4. verify court, docket, decision date, source detail, comments, Ready, and save;
5. verify duplicate comments and the absence of duplicate-policy leakage to the next row;
6. compare workbook status, logs, and external state with the branch contract.

## Next gate

The shared SMD/DAR fallback was subsequently characterized and extracted after
separate approval. Its date precedence, counsel/main routing, interactability retry,
Ready-result, and dispatcher-boundary contracts are recorded in
`SMD_DAR_SELENIUM_EXTRACTION.md`.
