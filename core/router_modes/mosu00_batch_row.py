"""MOSU00 table-document row orchestration."""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from .batch_policy import get_missing_metadata_policy


@dataclass(frozen=True)
class Mosu00RowOutcome:
    continue_to_form: bool
    metadata: Any = None
    row_status: Optional[str] = None


def process_mosu00_document_row(router, row_handler, full_index, row, lni, file_path):
    row_handler.record_metadata(router, full_index, row, lni, metadata_status="Attempted")
    if not router.search_lni(lni) or not router.check_result_available():
        row_handler.record_metadata(router, full_index, row, lni, metadata_status="Search Failed")
        return Mosu00RowOutcome(False, row_status="ERROR: LNI NOT FOUND")

    metadata = router.extract_mosu00_metadata_from_search_result(
        row, full_index, file_path=file_path
    )
    if not metadata:
        policy = get_missing_metadata_policy("mosu00")
        row_handler.record_metadata(
            router, full_index, row, lni, metadata_status=policy.metadata_status
        )
        logging.warning(
            "Skipping MOSU00 row %d: required table HTML metadata could not be extracted.",
            full_index + 2,
        )
        return Mosu00RowOutcome(False, row_status=policy.row_status)

    row_handler.record_metadata(
        router, full_index, row, lni, metadata=metadata, metadata_status="Extracted"
    )
    router.click_matching_result()
    return Mosu00RowOutcome(True, metadata=metadata)
