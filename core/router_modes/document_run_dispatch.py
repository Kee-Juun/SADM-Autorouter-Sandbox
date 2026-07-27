"""Document-only run dispatch behind the legacy process-rows boundary."""

from dataclasses import dataclass
import logging
from typing import Any, Optional

from .batch_policy import get_document_batch_policy


DOCUMENT_MODE_FLAG_PRECEDENCE = (
    ("mspb_mode", "mspb"),
    ("itc_mode", "itc"),
    ("irsplr_mode", "irsplr"),
    ("ohtax0_mode", "ohtax0"),
    ("mnsutb_mode", "mnsutb"),
)


@dataclass(frozen=True)
class DocumentRunOutcome:
    """Data returned to ``process_rows()`` after one document-only run."""

    mode_key: str
    counsel_df: Any
    main_df: Any
    processed_count: int
    duration: float


def dispatch_document_run(
    router,
    full_df,
    filtered_counsel_df,
    filtered_main_df,
    file_path,
    update_progress,
    *,
    dar_mode=False,
    wc_mode=False,
    mspb_mode=False,
    itc_mode=False,
    irsplr_mode=False,
    ohtax0_mode=False,
    mnsutb_mode=False,
) -> Optional[DocumentRunOutcome]:
    """Run the first active document mode using legacy precedence."""

    flag_values = {
        "mspb_mode": mspb_mode,
        "itc_mode": itc_mode,
        "irsplr_mode": irsplr_mode,
        "ohtax0_mode": ohtax0_mode,
        "mnsutb_mode": mnsutb_mode,
    }
    mode_key = next(
        (
            candidate
            for flag_name, candidate in DOCUMENT_MODE_FLAG_PRECEDENCE
            if flag_values[flag_name]
        ),
        None,
    )
    if mode_key is None:
        return None

    policy = get_document_batch_policy(mode_key)
    label = mode_key.upper()
    if policy.uses_filtered_main:
        counsel_df = filtered_counsel_df
        main_df = filtered_main_df
    else:
        counsel_df = full_df.iloc[0:0].copy()
        main_df = full_df.copy()
        logging.info(f"{label} Count: %d", len(main_df))

    logging.info(f"=== Starting {label} Batch ===")
    if router.set_status:
        router.set_status(policy.started_status)

    batch_kwargs = {}
    if policy.process_batch_flag:
        batch_kwargs[policy.process_batch_flag] = True
    processed_count, duration = router.process_batch(
        main_df,
        full_df,
        file_path,
        update_progress,
        policy.batch_type,
        dar_mode,
        wc_mode,
        **batch_kwargs,
    )

    if router.set_status:
        router.set_status(policy.processed_status)
    if processed_count > 0:
        total_mins = int(duration // 60)
        total_secs = int(duration % 60)
        logging.info(
            f"[{label} PROCESSING SUMMARY] {label}: %d LNIs "
            "processed in %dm %ds",
            processed_count,
            total_mins,
            total_secs,
        )

    return DocumentRunOutcome(
        mode_key=mode_key,
        counsel_df=counsel_df,
        main_df=main_df,
        processed_count=processed_count,
        duration=duration,
    )
