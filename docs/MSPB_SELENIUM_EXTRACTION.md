# MSPB Selenium Extraction

Status: third Phase 5 slice implemented  
Scope: MSPB IRT form-routing flow only

## New boundary

`core/router_modes/mspb_selenium.py` owns the MSPB form-routing sequence that formerly
lived in `CaseLawRouter.fill_mspb_irt_form()`.

The router method keeps its signature and delegates to the extracted function.
Existing handler lookup and callers therefore remain compatible.

MSPB PDF acquisition, browser-tab metadata discovery, parsing, downloads, and
`handle_mspb_fields()` have not moved.

## Preserved behavior contract

No-driver tests passed against the original and extracted implementations. They lock:

- missing-metadata skip result and status;
- disabled route plus enabled comments as `ALREADY PROCESSED`;
- filename, decision date, docket, and court common-field arguments;
- `Outside Conversion` and route change-event dispatch;
- five alert checks on the successful path;
- Ready to Process and final save arguments.

The full suite passed 43 tests at extraction.

## Live validation not performed

No authenticated staging or production route was executed. A live smoke test requires
a safe MSPB staging record and explicit authorization to modify external routing state.

Recommended checks:

1. capture the record's initial state;
2. verify PDF-derived court, docket, date, source detail, and comments;
3. verify `Outside Conversion`, Ready to Process, save, and workbook status;
4. repeat with an already-processed record;
5. compare logs and external state with the characterization contract.

## Subsequent work

After separate approval and richer branch tests, IRSPLR became the fourth extracted
form flow. ITC remains separately gated.
