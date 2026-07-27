"""Router session-loss classification and remaining-row status policy."""

from dataclasses import dataclass
import logging

from ..rerun_status import STATUS_NEEDS_RERUN_INTERRUPTED
from ..smducar_config import status_updates_buffer


@dataclass(frozen=True)
class BatchSessionLossOutcome:
    """Outer-loop instruction after one row loses the router session."""

    stop_batch: bool = True


def handle_batch_session_loss(
    router,
    df,
    full_index,
    row,
    error,
    error_entries,
) -> BatchSessionLossOutcome:
    """Record the existing row-level router-session-loss side effects."""

    logging.error(
        f"Router session lost while processing row "
        f"{full_index + 2}: {error}"
    )
    router._mark_remaining_rows_after_router_session_loss(
        df,
        full_index,
        str(error),
    )
    error_entries.append(
        {
            "Row": full_index + 2,
            "LNI": row.get("LNI", ""),
            "File Name": row.get("FileName", ""),
            "Status": "ERROR: ROUTER SESSION LOST",
            "Error Message": str(error),
        }
    )
    return BatchSessionLossOutcome()


def is_invalid_session_error(error):
    """Return whether an error contains a recognized lost-session marker."""

    error_text = str(error or "").lower()
    return any(
        marker in error_text
        for marker in (
            "invalid session id",
            "chrome not reachable",
            "disconnected",
            "not connected to devtools",
            "target window already closed",
            "no such window",
        )
    )


def raise_if_invalid_session_error(
    router,
    error,
    context="browser action",
    *,
    session_lost_error_type,
):
    """Raise the router exception with the original error chained."""

    if router._is_invalid_session_error(error):
        raise session_lost_error_type(
            f"Router browser session lost during {context}: {error}"
        ) from error


def mark_remaining_rows_after_router_session_loss(
    df,
    current_full_index,
    message,
):
    """Mark assigned rows from the current index onward for rerun."""

    mark_rows = False
    for remaining_index in df.index:
        if remaining_index == current_full_index:
            mark_rows = True
        if not mark_rows:
            continue

        row_status = str(
            status_updates_buffer.get(remaining_index)
            or df.loc[remaining_index].get("Status", "")
        ).strip().upper()
        if row_status in {"DONE", "ALREADY PROCESSED"}:
            continue
        status_updates_buffer[remaining_index] = (
            STATUS_NEEDS_RERUN_INTERRUPTED
        )

    logging.error(
        "Router session lost; remaining assigned rows were marked for rerun. %s",
        message,
    )
