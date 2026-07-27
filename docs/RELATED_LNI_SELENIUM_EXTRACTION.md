# SMD/DAR Related-LNI Selenium Extraction

Status: fifth helper slice implemented  
Scope: related counsel/recycled-LNI discovery, attachment, and verification

## New boundary

`core/router_modes/related_lni_selenium.py` owns the sequence formerly implemented by
`CaseLawRouter.handle_related_ln_is()`.

The router method retains its exact signature as a thin compatibility entry point.
The main-opinion module continues calling that method. Docket formatting is supplied
explicitly from `CaseLawRouter`, while LNI classification remains delegated to
`get_related_counsel_lnis()`.

`file_path` is retained because it is part of the public method signature. The
characterized implementation does not read it and performs no filesystem checks.

## Preserved contract

No-driver tests passed against both implementations and lock:

- exact docket formatting and DAR/WC arguments;
- recycled-LNI and dataframe arguments passed to `get_related_counsel_lnis()`;
- no candidates producing `NO COUNSEL ATTACHED`;
- existing list-box LNIs being skipped and still counting as success;
- invalid blank/`nan` candidate suppression;
- Related LNI input followed by Add and long-wait verification;
- locked input producing `RELATED LNI FIELD LOCKED`;
- timeout detection, five-minute user message, `show_error()`, and
  `RELATED LNI TIMEOUT`;
- final list-box reread and `NO COUNSEL ATTACHED` when no candidate is verified;
- outer failures producing `RELATED LNI ERROR`;
- exact Boolean return contract;
- a thin router wrapper and no filesystem coupling in the extracted module.

The full suite passed 102 tests after extraction.

## Live validation not performed

No browser, authenticated staging, or production record was used. Controlled
validation requires explicit authorization and safe main opinions covering existing,
new, recycled, locked, duplicate/already-existing, timeout, and unverified LNIs.

Recommended checks:

1. verify discovery order for counsel and recycled LNIs;
2. verify existing LNI suppression;
3. verify input, Add, and list-box confirmation;
4. verify locked and timeout statuses/messages;
5. verify final list-box validation;
6. compare workbook status, logs, and external state with the branch contract.

## Next gate

Pending-alert acceptance and duplicate classification were subsequently
characterized and extracted as the first recovery seam. Duplicate-overlay UI,
search/open navigation, tab lifecycle, session loss, and reopen behavior remain
separately gated. Controlled staging remains separately authorized.
