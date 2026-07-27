"""Shared LNI field submission and retry loop."""

import logging
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


def search_lni(
    router,
    lni_value,
    *,
    session_lost_error_type,
):
    """Search one LNI, refreshing Search Inventory between attempts."""

    max_retries = 3
    retry_delay = 2

    def recover_before_next_attempt(reason, attempt_number):
        if attempt_number >= max_retries:
            return
        logging.info(
            "Refreshing Search Inventory before LNI retry %d/%d for %s.",
            attempt_number + 1,
            max_retries,
            lni_value,
        )
        recovered = router.refresh_search_inventory_for_retry(
            reason=f"LNI search retry after {reason}"
        )
        if not recovered:
            logging.warning(
                "Search Inventory recovery did not fully confirm readiness "
                "before retrying LNI %s.",
                lni_value,
            )
        time.sleep(retry_delay)

    for attempt in range(1, max_retries + 1):
        try:
            if not router.check_session_validity():
                logging.error(
                    "Invalid session detected. Cannot proceed with LNI "
                    "search."
                )
                raise session_lost_error_type(
                    "Router browser session is no longer valid before LNI "
                    "search."
                )

            logging.info(
                "Search attempt %s for LNI: %s",
                attempt,
                lni_value,
            )

            search_field = router.search_wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="documentLNISearch"]')
                )
            )
            search_field.clear()
            time.sleep(0.5)
            search_field.send_keys(str(lni_value))
            time.sleep(0.5)

            search_button = router.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, '//*[@id="search"]')
                )
            )
            search_button.click()

            if router.check_result_available():
                logging.info(
                    "Successfully found results for LNI: %s",
                    lni_value,
                )
                return True

            logging.warning(
                "No results found for LNI on attempt %s/%s: %s",
                attempt,
                max_retries,
                lni_value,
            )
            recover_before_next_attempt(
                "no result appeared",
                attempt,
            )

        except Exception as error:
            error_msg = str(error)
            logging.error(
                "Search attempt %s failed: %s",
                attempt,
                error_msg,
            )

            if router._is_invalid_session_error(error):
                logging.error(
                    "Session invalid. Cannot retry - browser connection lost."
                )
                raise session_lost_error_type(
                    "Router browser session lost during LNI search for "
                    f"{lni_value}."
                ) from error

            recover_before_next_attempt(
                error_msg or "search exception",
                attempt,
            )

    logging.error(
        "All %s search attempts failed for LNI: %s",
        max_retries,
        lni_value,
    )
    return False
