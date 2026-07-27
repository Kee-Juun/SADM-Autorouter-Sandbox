"""Post-form batch-row status, duration, and timing-log helpers."""

from dataclasses import dataclass
import logging
from typing import Optional

from .batch_policy import form_status_replacement


@dataclass(frozen=True)
class BatchRowFinalizationOutcome:
    """Immutable counter increments after one row reaches form completion."""

    duration: float
    processed_increment: int
    replacement_status: Optional[str]


def finalize_batch_row(
    full_index,
    lni_start,
    form_status,
    *,
    status_buffer,
    clock,
) -> BatchRowFinalizationOutcome:
    """Apply status replacement, then read the existing LNI end clock."""

    replacement_status = form_status_replacement(
        status_buffer.get(full_index),
        form_status,
    )
    if replacement_status is not None:
        status_buffer[full_index] = replacement_status

    duration = clock() - lni_start
    return BatchRowFinalizationOutcome(
        duration=duration,
        processed_increment=1,
        replacement_status=replacement_status,
    )


def log_batch_row_duration(lni, duration):
    """Emit the existing per-LNI timing log after router counter updates."""

    logging.info(
        f"[LNI PROCESSING TIME] LNI {lni} processed in "
        f"{duration:.2f} seconds."
    )
