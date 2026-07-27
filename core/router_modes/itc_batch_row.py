"""ITC document-row orchestration behind the legacy router boundary."""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from .batch_policy import get_missing_metadata_policy


@dataclass(frozen=True)
class ItcRowOutcome:
    """Data returned to the outer batch loop after ITC preparation."""

    continue_to_form: bool
    metadata: Any = None
    row_status: Optional[str] = None


def process_itc_document_row(
    router,
    row_handler,
    full_index,
    row,
    lni,
) -> ItcRowOutcome:
    """Prepare one ITC row while leaving shared batch state to the caller."""

    row_handler.record_metadata(
        router,
        full_index,
        row,
        lni,
        metadata_status="Attempted",
    )

    if not router.search_lni(lni) or not router.check_result_available():
        row_handler.record_metadata(
            router,
            full_index,
            row,
            lni,
            metadata_status="Search Failed",
        )
        return ItcRowOutcome(
            continue_to_form=False,
            row_status="ERROR: LNI NOT FOUND",
        )

    metadata = row_handler.extract_metadata(router, row, full_index)
    if not metadata:
        missing_policy = get_missing_metadata_policy("itc")
        row_handler.record_metadata(
            router,
            full_index,
            row,
            lni,
            metadata_status=missing_policy.metadata_status,
        )
        logging.warning(
            "Skipping ITC row %d: required PDF metadata could not be "
            "extracted.",
            full_index + 2,
        )
        return ItcRowOutcome(
            continue_to_form=False,
            row_status=missing_policy.row_status,
        )

    metadata = row_handler.postprocess_metadata(
        router,
        full_index,
        row,
        lni,
        metadata,
    )
    row_handler.record_metadata(
        router,
        full_index,
        row,
        lni,
        metadata=metadata,
        metadata_status="Extracted",
    )
    router.click_matching_result()
    return ItcRowOutcome(
        continue_to_form=True,
        metadata=metadata,
    )
