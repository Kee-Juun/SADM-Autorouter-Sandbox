"""Selector-free dispatch for document-specific batch-row outcomes."""

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class DocumentRowOutcome:
    """Normalized result of optional document-specific row processing."""

    handled_document: bool
    handler_key: Optional[str]
    continue_to_form: bool
    row_status: Any = None
    mspb_metadata: Any = None
    itc_metadata: Any = None
    irsplr_metadata: Any = None
    ohtax0_metadata: Any = None
    mnsutb_metadata: Any = None


def dispatch_document_row_outcome(
    router,
    full_index,
    row,
    lni,
    *,
    mspb_mode=False,
    irsplr_mode=False,
    ohtax0_mode=False,
    mnsutb_mode=False,
    is_itc_row,
    is_irsplr_row,
    is_ohtax0_row,
    is_mnsutb_row,
    select_handler,
):
    """Select and invoke the existing document-row wrapper, if applicable."""

    row_is_itc = is_itc_row(row)
    row_is_irsplr = is_irsplr_row(row)
    row_is_ohtax0 = is_ohtax0_row(row)
    row_is_mnsutb = is_mnsutb_row(row)
    handler = select_handler(
        mspb_mode=mspb_mode,
        row_is_itc=row_is_itc,
        irsplr_mode=irsplr_mode,
        row_is_irsplr=row_is_irsplr,
        ohtax0_mode=ohtax0_mode,
        row_is_ohtax0=row_is_ohtax0,
        mnsutb_mode=mnsutb_mode,
        row_is_mnsutb=row_is_mnsutb,
    )

    if handler and handler.key == "mspb":
        wrapper_outcome = router.process_mspb_document_row(
            handler, full_index, row, lni
        )
        metadata_slot = "mspb_metadata"
    elif handler and handler.key == "itc":
        wrapper_outcome = router.process_itc_document_row(
            handler, full_index, row, lni
        )
        metadata_slot = "itc_metadata"
    elif handler and handler.key == "irsplr":
        wrapper_outcome = router.process_irsplr_document_row(
            handler, full_index, row, lni
        )
        metadata_slot = "irsplr_metadata"
    elif handler and handler.key == "ohtax0":
        wrapper_outcome = router.process_ohtax0_document_row(
            handler, full_index, row, lni
        )
        metadata_slot = "ohtax0_metadata"
    elif handler and handler.key == "mnsutb":
        wrapper_outcome = router.process_mnsutb_document_row(
            handler, full_index, row, lni
        )
        metadata_slot = "mnsutb_metadata"
    else:
        return DocumentRowOutcome(
            handled_document=False,
            handler_key=None,
            continue_to_form=True,
        )

    metadata = {metadata_slot: wrapper_outcome.metadata}
    return DocumentRowOutcome(
        handled_document=True,
        handler_key=handler.key,
        continue_to_form=wrapper_outcome.continue_to_form,
        row_status=wrapper_outcome.row_status,
        **metadata,
    )
