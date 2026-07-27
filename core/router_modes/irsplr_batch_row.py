"""IRSPLR document-row orchestration behind the legacy router boundary."""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from ..irsplr_extractor import build_irsplr_unreadable_fallback_metadata
from .batch_policy import get_missing_metadata_policy


@dataclass(frozen=True)
class IrsplrRowOutcome:
    """Data returned to the outer batch loop after IRSPLR preparation."""

    continue_to_form: bool
    metadata: Any = None
    row_status: Optional[str] = None


def process_irsplr_document_row(
    router,
    row_handler,
    full_index,
    row,
    lni,
) -> IrsplrRowOutcome:
    """Prepare one IRSPLR row while leaving shared batch state to the caller."""

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
        return IrsplrRowOutcome(
            continue_to_form=False,
            row_status="ERROR: LNI NOT FOUND",
        )

    metadata = row_handler.extract_metadata(router, row, full_index)
    if not metadata:
        missing_policy = get_missing_metadata_policy("irsplr")
        metadata = build_irsplr_unreadable_fallback_metadata(
            filename_hint=row.get("FileName", ""),
            court_code_hint=row.get("CourtCode", ""),
        )
        row_handler.record_metadata(
            router,
            full_index,
            row,
            lni,
            metadata=metadata,
            metadata_status=missing_policy.metadata_status,
        )
        logging.warning(
            "IRSPLR row %d PDF metadata could not be extracted; opening "
            "IRT form to check already-processed state.",
            full_index + 2,
        )
    else:
        row_handler.record_metadata(
            router,
            full_index,
            row,
            lni,
            metadata=metadata,
            metadata_status="Extracted",
        )

    router.click_matching_result()
    return IrsplrRowOutcome(
        continue_to_form=True,
        metadata=metadata,
    )
