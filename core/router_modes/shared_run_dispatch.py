"""Shared SMD/DAR counsel-and-main run orchestration."""

from dataclasses import dataclass
import logging
from typing import Any

from ..rerun_status import defer_main_rows_with_failed_counsel


@dataclass(frozen=True)
class SharedRunOutcome:
    """Data returned to ``process_rows()`` for final run handling."""

    counsel_df: Any
    main_df: Any
    counsel_count: int
    counsel_duration: float
    main_count: int
    main_duration: float


def dispatch_shared_run(
    router,
    counsel_df,
    main_df,
    full_df,
    file_path,
    update_progress,
    *,
    dar_mode=False,
    wc_mode=False,
    mosu00_mode=False,
) -> SharedRunOutcome:
    """Run counsel then eligible main rows using the existing contract."""

    logging.info(
        "=== Starting MOSU00 Counsel Batch ==="
        if mosu00_mode else "=== Starting Counsel Batch ==="
    )
    counsel_count, counsel_duration = router.process_batch(
        counsel_df,
        full_df,
        file_path,
        update_progress,
        "counsel",
        dar_mode,
        wc_mode,
        **({"mosu00_mode": True} if mosu00_mode else {}),
    )

    main_df, deferred_main_rows = defer_main_rows_with_failed_counsel(
        main_df,
        full_df,
        dar_mode=dar_mode,
        wc_mode=wc_mode,
    )
    if deferred_main_rows:
        logging.warning(
            "Deferred %d main opinion row(s) because required counsel "
            "did not finish cleanly.",
            len(deferred_main_rows),
        )

    if router.set_status:
        router.set_status("Counsel Batch Processed")

    try:
        while len(router.driver.window_handles) > 1:
            router.driver.switch_to.window(
                router.driver.window_handles[-1]
            )
            router.driver.close()
            router.driver.switch_to.window(
                router.driver.window_handles[0]
            )
        logging.info(
            "Cleaned up all leftover popup windows before Main Opinion "
            "batch."
        )
    except Exception:
        logging.warning("Failed to clean up extra windows")

    main_batch_type = "mosu00" if mosu00_mode else "main"
    main_batch_label = "MOSU00" if mosu00_mode else "Main Opinion"
    logging.info("=== Starting %s Batch ===", main_batch_label)
    if router.set_status:
        router.set_status(f"{main_batch_label} Batch Started")
    main_count, main_duration = router.process_batch(
        main_df,
        full_df,
        file_path,
        update_progress,
        main_batch_type,
        dar_mode,
        wc_mode,
        **({"mosu00_mode": True} if mosu00_mode else {}),
    )
    if router.set_status:
        router.set_status(f"{main_batch_label} Batch Processed")

    total_count = counsel_count + main_count
    total_time = counsel_duration + main_duration
    if total_count > 0:
        overall_avg = total_time / total_count
        overall_est_per_hour = int(3600 / overall_avg)
        total_mins = int(total_time // 60)
        total_secs = int(total_time % 60)
        counsel_mins = int(counsel_duration // 60)
        counsel_secs = int(counsel_duration % 60)
        main_mins = int(main_duration // 60)
        main_secs = int(main_duration % 60)

        logging.info(
            "[TOTAL AVERAGE PROCESSING TIME SUMMARY - LNI/HOUR "
            "ESTIMATE] TOTAL: %d LNIs successfully routed in %dm %ds",
            total_count,
            total_mins,
            total_secs,
        )
        logging.info(
            "    - Counsel: %d LNIs in %dm %ds",
            counsel_count,
            counsel_mins,
            counsel_secs,
        )
        logging.info(
            "    - %s: %d LNIs in %dm %ds",
            "Main/Table" if mosu00_mode else "Main Opinion",
            main_count,
            main_mins,
            main_secs,
        )
        logging.info(
            "    - Overall Avg: %.1fs/LNI → Est. %d LNIs/hour",
            overall_avg,
            overall_est_per_hour,
        )

    return SharedRunOutcome(
        counsel_df=counsel_df,
        main_df=main_df,
        counsel_count=counsel_count,
        counsel_duration=counsel_duration,
        main_count=main_count,
        main_duration=main_duration,
    )
