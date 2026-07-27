# Shared SMD/DAR Selenium Extraction

Status: sixth Phase 5 slice implemented  
Scope: shared SMD/DAR IRT form-routing fallback only

## New boundary

`core/router_modes/smd_dar_selenium.py` owns the shared SMD/DAR sequence formerly
embedded in `CaseLawRouter.fill_irt_form()`.

The router method remains the public compatibility entry point and still owns:

- required `FileName` and `LNI` row access;
- SMD/DAR counsel detection;
- specialized document-mode handler selection and precedence;
- the catch-all `ERROR` status boundary.

Only after no specialized handler is selected does it delegate to the shared module.
The router still owns common-field helpers, counsel/main field helpers, attachment and
related-LNI behavior, browser recovery helpers, and final save implementation.

## Preserved branch contract

No-driver tests passed against the implementation before and after extraction and
lock:

- manual Decision Date as the highest-priority date;
- counsel matching-main date and filename date fallback;
- Received-derived date as the final fallback;
- SMD main-opinion field handling and `Outside Conversion` routing;
- DAR/SMD counsel field handling and `Archive` routing;
- up to three interactability attempts for counsel and one for main opinions;
- counsel tab reopening between failed interactability attempts;
- `ROUTE ERROR`, `ALERT_HANDLED`, and `ALREADY PROCESSED` Ready outcomes;
- the legacy spaced `ROUTE ERROR` result for a Ready route alert;
- final save arguments and alert call order.

Structural tests keep specialized dispatch and the error boundary in
`CaseLawRouter.fill_irt_form()` while preventing shared counsel/main routing logic
from returning to that method. The full suite passed 66 tests after extraction.

## Live validation not performed

No authenticated staging or production route was executed. Controlled validation
requires explicit authorization and safe SMD and DAR records covering main opinions,
counsel, attachments, retries, already-processed forms, and Ready alerts.

Recommended checks:

1. verify SMD and DAR main opinions route to `Outside Conversion`;
2. verify counsel routes to `Archive`;
3. verify manual, filename, matching-main, and Received date precedence;
4. verify counsel retry/tab recovery and main non-interactable behavior;
5. verify Ready alert outcomes, comments, related LNIs, attachment handling, and save;
6. compare workbook statuses, logs, and external state with the branch contract.

## Next gate

All current form-routing sequences now have module boundaries. Common docket/date/
page/court preparation was subsequently extracted as a separately characterized
shared-helper slice. Further extraction of counsel/main field helpers,
attachment/related-LNI handling, navigation, retry, or save operations remains a new
higher-risk phase requiring its own approval. Controlled staging validation is also
a separate explicitly authorized action.
