"""Generic batch-row error recording without browser cleanup."""

from dataclasses import dataclass
import logging
from typing import Optional


@dataclass(frozen=True)
class BatchRowErrorOutcome:
    """Mode metadata recorded before the router performs local cleanup."""

    mode_key: Optional[str]
    metadata_status: Optional[str]


def record_batch_row_error(
    router,
    full_index,
    row,
    error,
    *,
    mspb_mode,
    metadata_buffer,
    status_buffer,
    error_entries,
    is_itc_row,
    is_irsplr_row,
    is_ohtax0_row,
    is_mnsutb_row,
    is_mework_row=lambda _row: False,
    is_mosu00_table_row=lambda _row: False,
) -> BatchRowErrorOutcome:
    """Record the existing generic row-error side effects in order."""

    logging.error(f"Error processing row {full_index + 2}")

    mode_key = None
    record_metadata = None
    if mspb_mode:
        mode_key = "mspb"
        record_metadata = router.record_mspb_metadata
    elif is_itc_row(row):
        mode_key = "itc"
        record_metadata = router.record_itc_metadata
    elif is_irsplr_row(row):
        mode_key = "irsplr"
        record_metadata = router.record_irsplr_metadata
    elif is_ohtax0_row(row):
        mode_key = "ohtax0"
        record_metadata = router.record_ohtax0_metadata
    elif is_mnsutb_row(row):
        mode_key = "mnsutb"
        record_metadata = router.record_mnsutb_metadata
    elif is_mework_row(row):
        mode_key = "mework"
        record_metadata = router.record_mework_metadata
    elif is_mosu00_table_row(row):
        mode_key = "mosu00"
        record_metadata = router.record_mosu00_metadata

    metadata_status = None
    if record_metadata is not None:
        existing_status = metadata_buffer.get(
            full_index,
            {},
        ).get("Metadata Status", "")
        metadata_status = (
            "Extracted" if existing_status == "Extracted" else "Error"
        )
        record_metadata(
            full_index,
            row,
            row.get("LNI", ""),
            metadata_status=metadata_status,
        )

    status_buffer[full_index] = "ERROR"
    error_entries.append(
        {
            "Row": full_index + 2,
            "LNI": row.get("LNI", ""),
            "File Name": row.get("FileName", ""),
            "Status": "ERROR",
            "Error Message": str(error),
        }
    )
    return BatchRowErrorOutcome(
        mode_key=mode_key,
        metadata_status=metadata_status,
    )
