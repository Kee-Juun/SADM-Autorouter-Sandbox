"""Selector-free shared-search, form-open, and refresh-retry transition."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BatchFormTransitionOutcome:
    """Normalized result returned to the batch outer-loop controller."""

    continue_to_finalization: bool
    form_status: Any = None
    row_status: Any = None


def process_batch_form_transition(
    router,
    row,
    full_df,
    full_index,
    file_path,
    lni,
    document_outcome,
    *,
    dar_mode=False,
    wc_mode=False,
    mspb_mode=False,
):
    """Run the existing browser-adjacent transition without applying loop state."""

    if not document_outcome.handled_document:
        if not router.handle_lni_search(lni):
            return BatchFormTransitionOutcome(
                continue_to_finalization=False,
                row_status="ERROR: LNI NOT FOUND",
            )

    form_kwargs = {
        "dar_mode": dar_mode,
        "wc_mode": wc_mode,
        "mspb_mode": mspb_mode,
        "mspb_metadata": document_outcome.mspb_metadata,
        "itc_metadata": document_outcome.itc_metadata,
        "irsplr_metadata": document_outcome.irsplr_metadata,
        "ohtax0_metadata": document_outcome.ohtax0_metadata,
        "mnsutb_metadata": document_outcome.mnsutb_metadata,
    }
    mework_metadata = getattr(document_outcome, "mework_metadata", None)
    if mework_metadata is not None:
        form_kwargs["mework_metadata"] = mework_metadata
    mosu00_metadata = getattr(document_outcome, "mosu00_metadata", None)
    if mosu00_metadata is not None:
        form_kwargs["mosu00_metadata"] = mosu00_metadata
    form_status = router.open_and_process_form(
        row,
        full_df,
        full_index,
        file_path,
        **form_kwargs,
    )

    if router._should_refresh_retry_form_status(form_status, full_index):
        form_status = router._refresh_and_retry_current_row(
            row,
            full_df,
            full_index,
            file_path,
            form_status,
            **form_kwargs,
        )

    return BatchFormTransitionOutcome(
        continue_to_finalization=True,
        form_status=form_status,
    )
