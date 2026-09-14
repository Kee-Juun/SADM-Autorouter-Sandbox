"""Batch throughput calculation and legacy summary logging."""

import logging


def log_batch_throughput_summary(
    *,
    processed_count,
    total_duration,
    batch_start_time,
    batch_type,
    clock,
):
    """Log the existing batch summary using the caller-supplied clock."""

    avg = total_duration / processed_count
    est_per_hour = int(3600 / avg)
    elapsed = clock() - batch_start_time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)
    logging.info(
        "[AVERAGE BATCH PROCESSING TIME - LNI/HOUR ESTIMATE] "
        f"Successfully routed {processed_count} {batch_type} LNIs in "
        f"{mins}m {secs}s "
        f"(Avg: {avg:.2f}s/LNI → Est. {est_per_hour} LNIs/hour)"
    )
