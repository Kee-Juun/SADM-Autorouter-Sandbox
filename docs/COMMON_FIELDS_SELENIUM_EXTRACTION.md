# Common Fields Selenium Extraction

Status: first shared-helper slice implemented  
Scope: common IRT docket/date/page/court preparation only

## New boundary

`core/router_modes/common_fields_selenium.py` owns the common-field preparation
sequence formerly implemented by `CaseLawRouter.prepare_common_fields()`.

The router method retains its exact signature as a thin compatibility entry point.
Every existing form-routing module continues calling that router method, so caller
shape and routing-module ownership are unchanged.

The extracted helper delegates actual interactions to the existing router methods:

- `get_decision_date_from_received()`;
- `safe_fill_field()`;
- `select_dropdown_by_visible_text_or_value()`.

The formatter remains explicitly supplied from `CaseLawRouter` to preserve the
previous static formatter dependency.

## Preserved contract

No-driver tests passed against both implementations and lock:

- `docket_override` taking precedence over filename docket formatting;
- exact `dar_mode` and `wc_mode` formatter arguments;
- a missing/falsy decision date using the Received-derived fallback;
- explicit decision dates avoiding that fallback;
- Number of Pages, Docket Number, and Decision Date field order and arguments;
- optional Court selection only when a court value is supplied;
- a thin compatibility method and a mode-neutral extracted module.

The legacy unused local dropdown helper was retained in the extracted module rather
than silently removed. The full suite passed 71 tests after extraction.

## Live validation not performed

No browser, authenticated staging, or production route was executed. This slice does
not change selectors or the underlying field/dropdown helper implementations.

Controlled staging checks, if separately authorized, should compare page count,
docket, decision date, and court values across SMD, DAR, and one specialized document
mode.

## Next gate

Final route/save and invalid-routing-combination retry behavior was subsequently
characterized and extracted after separate approval. The remaining candidates are
materially larger and more coupled:

- SMD/DAR counsel and main-opinion field helpers;
- related-LNI and attachment handling;
- navigation, tab recovery, and alert/duplicate recovery.

Each requires its own baseline and explicit approval. No deeper extraction is implied
by this shared-helper slice.
