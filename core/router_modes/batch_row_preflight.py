"""Batch-row completed/invalid/processable preflight decision."""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from .batch_policy import completed_row_status


@dataclass(frozen=True)
class BatchRowPreflightOutcome:
    """Decision returned before LNI timing and mode dispatch begin."""

    action: str
    should_process: bool
    lni: Any = None
    row_status: Optional[str] = None


def prepare_batch_row(
    router,
    row,
    full_index,
    file_path,
    *,
    status_buffer,
    mark_processing,
) -> BatchRowPreflightOutcome:
    """Apply the existing completed, validation, and processing sequence."""

    row_status = completed_row_status(row.get("Status", ""))
    if row_status:
        logging.info(
            f"Skipping completed row {full_index + 2} with status: "
            f"{row_status}."
        )
        status_buffer[full_index] = row_status
        return BatchRowPreflightOutcome(
            action="completed",
            should_process=False,
            row_status=row_status,
        )

    lni = router.validate_row(row, full_index, file_path)
    if not lni:
        return BatchRowPreflightOutcome(
            action="invalid",
            should_process=False,
        )

    mark_processing(full_index)
    return BatchRowPreflightOutcome(
        action="process",
        should_process=True,
        lni=lni,
    )
