# MNSUTB Selenium Extraction

Status: second Phase 5 slice implemented  
Scope: MNSUTB IRT form-routing flow only

## New boundary

`core/router_modes/mnsutb_selenium.py` owns the MNSUTB form-routing sequence that
previously lived in `CaseLawRouter.fill_mnsutb_irt_form()`.

The `CaseLawRouter` method keeps the same signature and is now a thin compatibility
entry point. The extracted flow continues to call the router's shared operations,
including `handle_mnsutb_fields()`, alert handling, Ready to Process, final save, and
driver/window cleanup.

Metadata acquisition, PDF parsing, and the MNSUTB field-fill helper have not moved.

## Preserved behavior contract

No-driver characterization tests passed against both the original and extracted flow.
They lock:

- missing-metadata skip result and status;
- disabled route plus enabled comments as `ALREADY PROCESSED`;
- common fields with the existing `court=None` argument;
- `Outside Conversion` selection and change-event dispatch;
- five successful-path alert checks;
- Ready to Process and final save arguments.

The full suite passed 38 tests at extraction.

## Live validation not performed

No authenticated staging or production route was executed. Live validation requires a
safe MNSUTB staging record and explicit authorization to modify that external state.

Recommended staging checks:

1. capture a safe record's initial state;
2. verify docket/date preparation and the existing court handling;
3. verify MNSUTB source detail/comments;
4. verify `Outside Conversion`, Ready to Process, save, and workbook status;
5. repeat with an already-processed record;
6. compare logs and external state with the characterization contract.

## Subsequent work

After separate approval, MSPB became the third extracted form flow using the same
baseline-first process. ITC and IRSPLR remain separately gated.

After an explicit business-compliance instruction, MNSUTB metadata Source Detail was
changed from `Order` to `Table-(5-day spec source)`. This is a deliberate behavior
change rather than part of the original behavior-preserving extraction. See
`MNSUTB_SOURCE_DETAIL_COMPLIANCE.md`.
