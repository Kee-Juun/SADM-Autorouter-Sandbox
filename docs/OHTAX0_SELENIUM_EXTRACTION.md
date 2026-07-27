# OHTAX0 Selenium Extraction

Status: first Phase 5 slice implemented  
Scope: OHTAX0 IRT form-routing flow only

## New boundary

`core/router_modes/ohtax0_selenium.py` now owns the OHTAX0 form-routing sequence that
previously lived in `CaseLawRouter.fill_ohtax0_irt_form()`.

`CaseLawRouter.fill_ohtax0_irt_form()` remains available with the same signature and
delegates to the extracted function. Existing mode handlers and callers therefore keep
the same public entry point.

The extracted flow still calls shared router operations for:

- common-field preparation;
- OHTAX0-specific field filling;
- alert handling;
- Ready to Process handling;
- final route/save handling;
- driver close and window switching.

OHTAX0 metadata discovery, PDF parsing, and `handle_ohtax0_fields()` remain in their
existing modules. No other mode's Selenium flow moved in this slice.

## Preserved behavior contract

The no-driver characterization tests lock:

- missing-metadata skip result and status;
- disabled route plus enabled comments as `ALREADY PROCESSED`;
- exact common-field arguments;
- `Outside Conversion` route selection;
- route change-event dispatch;
- five alert checks on the successful path;
- Ready to Process invocation;
- final `handle_routing_and_save()` arguments and return value.

The broader suite continues to cover registry ordering, flag and scope precedence,
handler selection, metadata delegation, and workflow scope integration.

## Validation performed

```text
python -B -m unittest discover -s tests -v
```

Result at extraction: 32 tests passed.

These tests use mocks and an uninitialized router shell. They do not create Chrome or
write to an external routing environment.

## Live validation not performed

No authenticated staging or production route was executed. A live route can change
external document state and therefore requires an explicitly selected safe staging
record, credentials/session availability, and authorization for that state change.

Before extracting another Selenium mode, the recommended live smoke checklist is:

1. select a safe OHTAX0 staging record and preserve its starting state;
2. run with visible Chrome and capture the emitted statuses;
3. verify common fields, source detail/comments, and `Outside Conversion`;
4. verify Ready to Process, save result, and workbook status;
5. exercise an already-processed record;
6. compare logs and final external state with the documented contract.

## Subsequent work

After review and separate approval, the MNSUTB form flow was extracted using the same
baseline-first pattern. Further modes remain separately gated.
