"""Shared-run success state and optional legacy error-report output."""

import datetime
import logging
from pathlib import Path

import pandas as pd


def finalize_shared_run(router, error_entries):
    """Apply the existing shared-run success and report side effects."""

    router._last_success_log_time = datetime.datetime.now()
    router._success_message_dismissed = False

    # This will be overridden by the dynamic message in the GUI.
    logging.info("Documents Auto-Routed Successfully!")

    if router.set_status:
        router.set_status("Success!")

    if error_entries:
        error_df = pd.DataFrame(error_entries)
        timestamp = (
            datetime.datetime.now()
            .strftime("%I-%M-%S_%p")
            .lstrip("0")
        )
        error_folder = (
            Path.home()
            / "Downloads"
            / "Case Law Auto-Routing Resources"
            / "Error Reports"
        )
        error_folder.mkdir(parents=True, exist_ok=True)
        error_path = error_folder / f"Error Report - {timestamp}.xlsx"
        error_df.to_excel(error_path, index=False)
        logging.info(f"Error report saved to {error_path}")
