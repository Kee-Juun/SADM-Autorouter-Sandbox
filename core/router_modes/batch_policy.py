"""Pure policy values used by batch and run-level router orchestration."""

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Optional


SUPPORTED_PROGRESS_BATCHES = frozenset(
    {
        "counsel",
        "main",
        "mspb",
        "itc",
        "irsplr",
        "ohtax0",
        "mnsutb",
    }
)

COMPLETED_ROW_STATUSES = frozenset({"DONE", "ALREADY PROCESSED"})
STATUS_PROCESSING = "PROCESSING"


def is_progress_batch(batch_type) -> bool:
    """Return whether the legacy callback recognizes ``batch_type``."""

    return batch_type in SUPPORTED_PROGRESS_BATCHES


def emit_batch_progress(
    update_progress,
    batch_type,
    completed_rows,
    total_rows,
) -> bool:
    """Emit the legacy progress callback when the batch is supported."""

    if not update_progress or not is_progress_batch(batch_type):
        return False
    update_progress(batch_type, completed_rows, total_rows)
    return True


def completed_row_status(status) -> Optional[str]:
    """Return the normalized terminal row status, otherwise ``None``."""

    normalized = str(status).strip().upper()
    return normalized if normalized in COMPLETED_ROW_STATUSES else None


def _normalized_status(status) -> str:
    if status is None:
        return ""
    try:
        unequal_to_self = status != status
        if isinstance(unequal_to_self, bool) and unequal_to_self:
            return ""
    except Exception:
        pass
    text = str(status).strip()
    if text.lower() in {"nan", "<na>", "nat"}:
        return ""
    return text.upper()


def form_status_replacement(
    current_status,
    form_status,
) -> Optional[str]:
    """Return the status that should replace buffered ``PROCESSING``."""

    try:
        if not form_status:
            return None
    except Exception:
        pass

    if _normalized_status(form_status) in COMPLETED_ROW_STATUSES:
        return None
    if _normalized_status(current_status) != STATUS_PROCESSING:
        return None
    return str(form_status).strip().upper()


@dataclass(frozen=True)
class MissingMetadataPolicy:
    mode_key: str
    action: str
    metadata_status: str
    row_status: Optional[str]


MISSING_METADATA_POLICIES: Mapping[str, MissingMetadataPolicy] = (
    MappingProxyType(
        {
            "mspb": MissingMetadataPolicy(
                mode_key="mspb",
                action="skip",
                metadata_status="Not Extracted",
                row_status="SKIPPED: MSPB PDF DATA NOT FOUND",
            ),
            "itc": MissingMetadataPolicy(
                mode_key="itc",
                action="skip",
                metadata_status="Not Extracted",
                row_status="SKIPPED: ITC PDF DATA NOT FOUND",
            ),
            "irsplr": MissingMetadataPolicy(
                mode_key="irsplr",
                action="fallback",
                metadata_status="Unreadable PDF Fallback",
                row_status=None,
            ),
            "ohtax0": MissingMetadataPolicy(
                mode_key="ohtax0",
                action="skip",
                metadata_status="Not Extracted",
                row_status="SKIPPED: OHTAX0 PDF DATA NOT FOUND",
            ),
            "mnsutb": MissingMetadataPolicy(
                mode_key="mnsutb",
                action="skip",
                metadata_status="Not Extracted",
                row_status="SKIPPED: MNSUTB PDF DATA NOT FOUND",
            ),
        }
    )
)


def get_missing_metadata_policy(mode_key: str) -> MissingMetadataPolicy:
    return MISSING_METADATA_POLICIES[mode_key]


@dataclass(frozen=True)
class DocumentBatchPolicy:
    mode_key: str
    batch_type: str
    started_status: str
    processed_status: str
    uses_filtered_main: bool
    process_batch_flag: Optional[str]


DOCUMENT_BATCH_POLICIES: Mapping[str, DocumentBatchPolicy] = MappingProxyType(
    {
        "mspb": DocumentBatchPolicy(
            mode_key="mspb",
            batch_type="mspb",
            started_status="MSPB Batch Started",
            processed_status="MSPB Batch Processed",
            uses_filtered_main=True,
            process_batch_flag="mspb_mode",
        ),
        "itc": DocumentBatchPolicy(
            mode_key="itc",
            batch_type="itc",
            started_status="ITC Batch Started",
            processed_status="ITC Batch Processed",
            uses_filtered_main=False,
            process_batch_flag=None,
        ),
        "irsplr": DocumentBatchPolicy(
            mode_key="irsplr",
            batch_type="irsplr",
            started_status="IRSPLR Batch Started",
            processed_status="IRSPLR Batch Processed",
            uses_filtered_main=False,
            process_batch_flag="irsplr_mode",
        ),
        "ohtax0": DocumentBatchPolicy(
            mode_key="ohtax0",
            batch_type="ohtax0",
            started_status="OHTAX0 Batch Started",
            processed_status="OHTAX0 Batch Processed",
            uses_filtered_main=False,
            process_batch_flag="ohtax0_mode",
        ),
        "mnsutb": DocumentBatchPolicy(
            mode_key="mnsutb",
            batch_type="mnsutb",
            started_status="MNSUTB Batch Started",
            processed_status="MNSUTB Batch Processed",
            uses_filtered_main=False,
            process_batch_flag="mnsutb_mode",
        ),
    }
)


def get_document_batch_policy(mode_key: str) -> DocumentBatchPolicy:
    return DOCUMENT_BATCH_POLICIES[mode_key]
