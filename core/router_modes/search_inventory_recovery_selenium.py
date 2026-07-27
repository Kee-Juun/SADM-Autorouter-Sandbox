"""Search Inventory readiness and refresh-recovery helpers."""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def is_search_inventory_ready(router, timeout=8):
    """Return whether the Search Inventory LNI field is present."""

    try:
        WebDriverWait(router.driver, timeout).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="documentLNISearch"]')
            )
        )
        return True
    except Exception as error:
        router._raise_if_invalid_session_error(
            error,
            "Search Inventory readiness check",
        )
        return False


def refresh_search_inventory_for_retry(
    router,
    reason="recoverable form issue",
):
    """Refresh back to Search Inventory for an existing retry caller."""

    logging.warning(
        "Attempting Search Inventory refresh recovery after %s.",
        reason,
    )
    router._close_extra_tabs_and_focus_main()

    try:
        router.safe_alert_accept()
    except Exception as error:
        router._raise_if_invalid_session_error(
            error,
            "pre-refresh alert cleanup",
        )

    try:
        router.driver.refresh()
        WebDriverWait(router.driver, 25).until(
            lambda driver: driver.execute_script(
                "return document.readyState"
            )
            == "complete"
        )
        router.safe_alert_accept()
    except Exception as error:
        router._raise_if_invalid_session_error(
            error,
            "refresh recovery",
        )
        logging.warning(
            "Refresh recovery could not refresh the current page: %s",
            error,
        )

    if router._is_search_inventory_ready(timeout=10):
        logging.info(
            "Search Inventory is ready after refresh recovery."
        )
        return True

    logging.info(
        "Search Inventory field was not visible after refresh; trying "
        "Search Inventory menu once."
    )
    if (
        router.click_search_inventory()
        and router._is_search_inventory_ready(timeout=15)
    ):
        logging.info(
            "Search Inventory reopened after refresh recovery."
        )
        return True

    logging.error(
        "Refresh recovery failed to reopen Search Inventory."
    )
    return False
