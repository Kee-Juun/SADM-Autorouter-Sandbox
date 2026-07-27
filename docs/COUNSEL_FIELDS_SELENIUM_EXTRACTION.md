# SMD/DAR Counsel Fields Selenium Extraction

Status: third shared-helper slice implemented  
Scope: SMD/DAR counsel comments and main-opinion LNI linkage only

## New boundary

`core/router_modes/counsel_fields_selenium.py` owns the sequence formerly implemented
by `CaseLawRouter.handle_counsel_fields()`.

The router method retains its exact signature as a thin compatibility entry point.
The shared SMD/DAR form flow continues calling that method. Router ownership of the
full mapping dataframe, docket formatter, duplicate-popup handler, Selenium wait, and
driver is unchanged.

## Preserved contract

No-driver tests passed against both implementations and lock:

- counsel filename docket formatting with exact `dar_mode` and `wc_mode` arguments;
- scanning the full mapping dataframe in its existing order;
- excluding counsel rows from main-opinion candidates;
- matching candidate docket numbers before attaching LNIs;
- skipping LNIs already contained in existing comments;
- main-opinion LNIs preceding mapping-sheet comments;
- removing a trailing period before semicolon concatenation;
- returning without a write when no new content exists;
- duplicate-document alert acceptance, popup handling, and field refill;
- two comment-write attempts with a one-second delay between failures;
- swallowed comments lookup/write errors and the existing `None` return contract;
- a thin router compatibility method and counsel-only extracted module.

The full suite passed 85 tests after extraction.

## Live validation not performed

No browser, authenticated staging, or production record was used. Controlled
validation requires explicit authorization and safe counsel rows with matching,
already-linked, multiple-main-LNI, mapping-comment, duplicate-alert, and retry cases.

Recommended checks:

1. compare SMD and DAR docket matching;
2. verify main-opinion LNI ordering and duplicate suppression;
3. verify punctuation and mapping-comment concatenation;
4. verify duplicate-popup refill behavior;
5. verify retry behavior and final displayed comments;
6. compare workbook logs and external state with the branch contract.

## Next gate

Main-opinion case/source/Related/comments composition was subsequently characterized
and extracted after separate approval. Related-LNI and attachment implementation
remains delegated to the router and requires its own broader baseline. Navigation,
tab recovery, and alert/duplicate internals remain independently gated.
