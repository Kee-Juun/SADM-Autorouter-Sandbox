# Routing and Save Selenium Extraction

Status: second shared-helper slice implemented  
Scope: final route, Ready, Save, and invalid-combination retry flow

## New boundary

`core/router_modes/routing_save_selenium.py` owns the sequence formerly implemented
by `CaseLawRouter.handle_routing_and_save()`.

The router method retains its exact signature as a thin compatibility entry point.
All specialized and shared SMD/DAR routing modules continue calling that method, so
their call shapes and ownership boundaries are unchanged.

The extracted helper delegates alert, duplicate-overlay, Ready, click, reopen, and
browser-window operations to existing router helpers.

## Preserved contract

No-driver tests passed against both implementations and lock:

- `skip_route_and_ready=True` proceeding directly to Save;
- main documents selecting `Outside Conversion`;
- counsel documents selecting `Archive`;
- route change-event dispatch and alert checks;
- retry after an unexpected alert during the initial route click;
- `READY_NOT_CLICKABLE` producing `ALREADY PROCESSED`, status update, and tab cleanup;
- Save with no alert producing `DONE`;
- Save exceptions producing `ALREADY PROCESSED` with cleanup;
- the exact invalid ARC routing-combination alert detection;
- three Save attempts, two `attempt_open_modify()` calls, and final
  `INVALID ROUTING COMBO` status;
- a thin compatibility method and mode-neutral shared module.

The full suite passed 78 tests after extraction.

## Live validation not performed

No browser, authenticated staging, or production route was executed. Controlled
validation requires explicit authorization and safe records covering main, counsel,
already-processed, unexpected-alert, and invalid-routing-combination branches.

Recommended checks:

1. verify normal main and counsel route labels;
2. verify Ready and Save ordering;
3. verify unexpected-alert route recovery;
4. verify tab cleanup on already-processed and failed Save paths;
5. verify three-attempt Modify-entry behavior for the invalid ARC combination;
6. compare workbook status, logs, and external state with the branch contract.

## Next gate

SMD/DAR counsel field composition was subsequently characterized and extracted after
separate approval. The remaining extraction candidates are mode- or
navigation-specific:

- SMD/DAR main-opinion fields, related LNIs, and attachments;
- navigation, tab recovery, and alert/duplicate recovery internals.

Each remains a separately characterized and explicitly approved phase.

Modify-mode entry was subsequently characterized and extracted into
`modify_recovery_selenium.py`; duplicate-overlay UI and Search Inventory navigation
remain outside that boundary.
