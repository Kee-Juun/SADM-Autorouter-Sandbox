# SMD/DAR Main-Opinion Fields Selenium Extraction

Status: fourth helper slice implemented  
Scope: main-opinion case/source/Related/comments composition only

## New boundary

`core/router_modes/main_opinion_fields_selenium.py` owns the sequence formerly
implemented by `CaseLawRouter.handle_main_opinion_fields()`.

The router method retains its exact signature as a thin compatibility entry point.
The extracted module deliberately calls the unchanged
`CaseLawRouter.handle_related_ln_is()` compatibility method; discovery, validation,
and attachment of counsel/recycled LNIs remain in the router.

## Preserved contract

No-driver tests passed against both implementations and lock:

- blank Case Name being filled with `RE`;
- Source Detail resolution occurring before the Related checkbox click;
- Source Detail dropdown selection and duplicate-alert popup handling;
- Related checkbox click preceding related-LNI delegation;
- exact row, dataframe, index, path, DAR, and WC arguments to
  `handle_related_ln_is()`;
- preserving an existing related-LNI failure status;
- defaulting a missing failure status to `Missing Counsel Information`;
- tab cleanup when no related LNI can be attached;
- disabled Comments and Route producing `Non-interactable IRT Form`;
- existing comment punctuation and mapping-comment concatenation;
- two comment-write attempts with a one-second retry delay;
- the existing successful `None` return contract;
- a thin router wrapper and a structural prohibition on attachment implementation
  entering this module.

The full suite passed 93 tests after extraction.

## Live validation not performed

No browser, authenticated staging, or production record was used. Controlled
validation requires explicit authorization and safe main-opinion rows covering Source
Detail, related counsel, recycled LNIs, missing counsel, non-interactable forms,
duplicate alerts, and comment retries.

Recommended checks:

1. verify Case Name and Source Detail values;
2. verify Source Detail precedes Related;
3. verify duplicate-alert recovery;
4. verify related-LNI failure statuses and cleanup;
5. verify comment punctuation and retry behavior;
6. compare workbook status, logs, and external state with the branch contract.

## Next gate

`CaseLawRouter.handle_related_ln_is()` was subsequently characterized and extracted
after separate approval. The characterization confirmed that `file_path` is retained
for compatibility but the method performs no filesystem checks. Navigation, tab
recovery, and alert/duplicate internals remain independently gated.
