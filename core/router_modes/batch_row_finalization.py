"""Post-form batch-row status, duration, and timing-log helpers."""

from dataclasses import dataclass
import logging
from typing import Optional

from .batch_policy import form_status_replacement
from ..rerun_status import STATUS_DONE, is_completed_status, normalize_status


@dataclass(frozen=True)
class BatchRowFinalizationOutcome:
    """Immutable counter increments after one row reaches form completion."""

    duration: float
    processed_increment: int
    replacement_status: Optional[str]
    final_status: str


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
    normalized_form_status = normalize_status(form_status)
    final_status = (
        normalized_form_status
        if is_completed_status(normalized_form_status)
        else status_buffer.get(full_index) or form_status
    )
    return BatchRowFinalizationOutcome(
        duration=duration,
        processed_increment=int(normalize_status(final_status) == STATUS_DONE),
        replacement_status=replacement_status,
        final_status=normalize_status(final_status),
    )


def log_batch_row_duration(lni, duration, final_status=None):
    """Emit the existing per-LNI timing log after router counter updates."""

    normalized = normalize_status(final_status)
    if normalized == STATUS_DONE:
        logging.info(
            f"[LNI PROCESSING TIME] LNI {lni} routed and saved in "
            f"{duration:.2f} seconds."
        )
    elif is_completed_status(normalized):
        logging.info(
            f"[LNI PROCESSING TIME] LNI {lni} finished as {normalized} in "
            f"{duration:.2f} seconds."
        )
    else:
        logging.warning(
            f"[LNI PROCESSING TIME] LNI {lni} ended as "
            f"{normalized or 'UNKNOWN'} after {duration:.2f} seconds; "
            "not counted as successfully routed."
        )
