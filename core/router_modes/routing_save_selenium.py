"""Shared final route, Ready, and Save handling for router form flows."""

import logging

from selenium.common.exceptions import (
    TimeoutException,
    UnexpectedAlertPresentException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..smducar_config import status_updates_buffer


def handle_routing_and_save(
    router,
    is_counsel,
    row_index,
    skip_route_and_ready=False,
):
    """Run the existing route selection, Ready, Save, and retry sequence."""

    save_attempts = 3
    for attempt in range(save_attempts):
        try:
            if not skip_route_and_ready:
                route_element = router.driver.find_element(
                    By.XPATH,
                    '//*[@id="route"]',
                )
                router.driver.execute_script(
                    "arguments[0].scrollIntoView(true);",
                    route_element,
                )
                router.handle_any_alert(timeout=2)
                try:
                    try:
                        route_element.click()
                        dropdown = Select(route_element)
                        route_label = (
                            "Archive" if is_counsel else "Outside Conversion"
                        )
                        dropdown.select_by_visible_text(route_label)
                    except UnexpectedAlertPresentException:
                        router.handle_any_alert()
                        route_element = router.driver.find_element(
                            By.XPATH,
                            '//*[@id="route"]',
                        )
                        route_element.click()
                        dropdown = Select(route_element)
                        route_label = (
                            "Archive" if is_counsel else "Outside Conversion"
                        )
                        dropdown.select_by_visible_text(route_label)
                except Exception:
                    logging.warning(
                        "Exception during route selection. Attempting to handle "
                        "popups/overlays and retry."
                    )
                    router.handle_unexpected_alert()
                    router.handle_duplicate_overlay()
                    try:
                        router.handle_any_alert()
                        route_element = router.driver.find_element(
                            By.XPATH,
                            '//*[@id="route"]',
                        )
                        route_element.click()
                        dropdown = Select(route_element)
                        route_label = (
                            "Archive" if is_counsel else "Outside Conversion"
                        )
                        dropdown.select_by_visible_text(route_label)
                    except Exception as retry_error:
                        logging.error(
                            "Route selection failed after handling "
                            "popups/overlays: %s",
                            retry_error,
                        )
                        return "ROUTE DROPDOWN ERROR"
                router.driver.execute_script(
                    "document.getElementById('route').dispatchEvent("
                    "new Event('change'))"
                )
                logging.info("Selected route: %s", route_label)
                router.handle_any_alert(timeout=2)
                ready_result = router.click_ready_checkbox_and_check_overlay(
                    is_counsel
                )
                if ready_result == "READY_NOT_CLICKABLE":
                    logging.info(
                        "Ready to Process checkbox was not clickable during "
                        "routing; marking document as ALREADY PROCESSED."
                    )
                    if row_index is not None:
                        status_updates_buffer[row_index] = "ALREADY PROCESSED"
                    router.driver.close()
                    router.driver.switch_to.window(
                        router.driver.window_handles[0]
                    )
                    return "ALREADY PROCESSED"
                router.handle_any_alert(timeout=2)

            try:
                router.click_element('//*[@id="add"]')
                logging.info("Clicked Save button.")
                try:
                    WebDriverWait(router.driver, 3).until(
                        EC.alert_is_present()
                    )
                    alert = router.driver.switch_to.alert
                    alert_text = alert.text.strip()
                    alert.accept()
                    logging.info("Accepted alert: %s", alert_text)
                    if (
                        "route = [arc] vendorcode = [arc] workflow = [] "
                        "is not a valid routing combo"
                        in alert_text.lower()
                    ):
                        logging.warning(
                            "Invalid routing combo alert after save "
                            "(attempt %s). Closing form and retrying.",
                            attempt + 1,
                        )
                        router.driver.close()
                        router.driver.switch_to.window(
                            router.driver.window_handles[0]
                        )
                        if attempt < save_attempts - 1:
                            router.attempt_open_modify(row_index=row_index)
                            continue

                        logging.error(
                            "Failed to save LNI after %s attempts due to "
                            "invalid routing combo.",
                            save_attempts,
                        )
                        if row_index is not None:
                            status_updates_buffer[row_index] = (
                                "INVALID ROUTING COMBO"
                            )
                        return "INVALID ROUTING COMBO"
                except TimeoutException:
                    pass
                return "DONE"
            except Exception:
                logging.info(
                    "Save failed, assuming form already processed. "
                    "Closing window."
                )
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return "ALREADY PROCESSED"
        except Exception:
            if router.handle_unexpected_alert():
                logging.info(
                    "Continuing after handling an unexpected alert during "
                    "routing."
                )
            else:
                logging.error("Route selection failed")
            return "ROUTE DROPDOWN ERROR"

    logging.error(
        "Failed to save LNI after %s attempts due to invalid routing combo.",
        save_attempts,
    )
    if row_index is not None:
        status_updates_buffer[row_index] = "INVALID ROUTING COMBO"
    return "INVALID ROUTING COMBO"
