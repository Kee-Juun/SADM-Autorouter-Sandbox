"""Shared Modify-mode entry and alert recovery."""

import logging
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..smducar_config import status_updates_buffer


def attempt_open_modify(
    router,
    file_path=None,
    row_index=None,
    max_attempts=3,
    *,
    session_lost_error_type,
):
    """Attempt to enter Modify mode while preserving legacy retry behavior."""

    for attempt in range(1, max_attempts + 1):
        try:
            if not router.check_session_validity():
                logging.error(
                    "Invalid session detected. Cannot proceed with Modify "
                    "button click."
                )
                raise session_lost_error_type(
                    "Router browser session is no longer valid before "
                    "Modify click."
                )

            logging.info(
                "Attempt %s/%s: Waiting for Modify button...",
                attempt,
                max_attempts,
            )
            modify_btn = WebDriverWait(router.driver, 120).until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="modify"]'))
            )
            modify_btn.click()
            logging.info("Clicked Modify button.")

            try:
                alert = WebDriverWait(router.driver, 5).until(
                    EC.alert_is_present()
                )
                alert_text = alert.text.strip()
                alert.accept()
                logging.info("Accepted alert: %s", alert_text)

                if "ready to process = [on]" in alert_text.lower():
                    logging.info(
                        "IRT Form is not yet ready. Waiting 5 seconds before "
                        "retrying Modify click..."
                    )
                    time.sleep(5)
                    continue

                if "duplicate document" in alert_text.lower():
                    router.handle_duplicate_lni_popup()
                    return True

                if (
                    "dsar" in alert_text.lower()
                    and "duplicate" in alert_text.lower()
                ):
                    logging.info(
                        "DSAR duplicate alert detected. Checking for "
                        "additional duplicate document alert..."
                    )
                    time.sleep(2)
                    try:
                        additional_alert = WebDriverWait(
                            router.driver,
                            5,
                        ).until(EC.alert_is_present())
                        additional_alert_text = additional_alert.text.strip()
                        additional_alert.accept()
                        logging.info(
                            "Accepted additional alert after DSAR: %s",
                            additional_alert_text,
                        )

                        if (
                            "duplicate document"
                            in additional_alert_text.lower()
                        ):
                            router.handle_duplicate_lni_popup()
                            return True
                    except TimeoutException:
                        logging.info(
                            "No additional alert found after DSAR duplicate "
                            "alert."
                        )
            except TimeoutException:
                logging.info(
                    "No alert found. IRT Form is ready for editing."
                )
                return True

        except Exception as error:
            error_msg = str(error)
            logging.warning(
                "Attempt %s/%s to click Modify button failed: %s",
                attempt,
                max_attempts,
                error_msg,
            )

            if router._is_invalid_session_error(error):
                logging.error(
                    "Session invalid. Cannot retry - browser connection lost."
                )
                raise session_lost_error_type(
                    "Router browser session lost while opening Modify mode."
                ) from error

            time.sleep(2)

    logging.error(
        "Failed to enter modify mode after %s attempts.",
        max_attempts,
    )
    if row_index is not None:
        status_updates_buffer[row_index] = "ERROR: MODIFY FAILED"
    return False
