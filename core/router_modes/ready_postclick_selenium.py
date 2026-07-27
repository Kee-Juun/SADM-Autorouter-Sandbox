"""Ready-to-Process click and post-click alert/overlay state machine."""

import logging
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def click_ready_checkbox_and_check_overlay(router, is_counsel=True):
    """Click Ready and preserve the legacy post-click outcome contract."""

    ready_clicked = False
    try:
        last_ready_exception = None
        for attempt in range(1, 3):
            try:
                element = WebDriverWait(router.driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="readyToProcess"]')
                    )
                )
                router.driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});",
                    element,
                )
                time.sleep(0.25)
                element.click()
                ready_clicked = True
                logging.info("Clicked Ready to Process checkbox.")
                break
            except Exception as error:
                last_ready_exception = error
                if attempt < 2:
                    logging.info(
                        "Ready to Process checkbox was not clickable on "
                        "attempt %d/2; retrying.",
                        attempt,
                    )
                    router.handle_any_alert(timeout=1)
                    time.sleep(1)
        else:
            logging.info(
                "Ready to Process checkbox is not clickable; treating "
                "the document as already processed."
            )
            return "READY_NOT_CLICKABLE"

        router.handle_any_alert(timeout=2)
        handled_alert = False
        duplicate_handled = False
        while True:
            try:
                WebDriverWait(router.driver, 2).until(
                    EC.alert_is_present()
                )
                alert = router.driver.switch_to.alert
                alert_text = alert.text.strip()
                alert.accept()
                logging.warning(
                    "Got alert after Ready to Process: %s",
                    alert_text,
                )
                handled_alert = True
                if "duplicate document" in alert_text.lower():
                    logging.info(
                        "Duplicate alert detected after Ready to Process. "
                        "Handling..."
                    )
                    router.handle_duplicate_lni_popup()
                    duplicate_handled = True
                    continue
                if (
                    "document cannot be processed for route - inventory "
                    "route"
                    in alert_text.lower()
                ):
                    logging.info(
                        "Route alert indicates document is fresh. "
                        "Proceeding as fresh."
                    )
                    return True
                if (
                    "document cannot be processed until workflow is "
                    "selected"
                    in alert_text.lower()
                ):
                    logging.info(
                        "Workflow selection alert indicates document is "
                        "fresh. Proceeding as fresh."
                    )
                    return True
            except TimeoutException:
                break

        if duplicate_handled:
            try:
                WebDriverWait(router.driver, 5).until_not(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "ui-widget-overlay")
                    )
                )
                logging.info(
                    "Duplicate overlay cleared after handling. "
                    "Proceeding to Save."
                )
                router.click_element('//*[@id="add"]')
                logging.info(
                    "Clicked Save button after duplicate handling."
                )
                return True
            except Exception:
                logging.error(
                    "Error during fresh doc flow after duplicate overlay"
                )
                return False

        try:
            WebDriverWait(router.driver, 3).until(
                EC.presence_of_element_located(
                    (By.CLASS_NAME, "ui-widget-overlay")
                )
            )
            logging.info(
                "Popup overlay appeared after clicking Ready to Process. "
                "Document is fresh."
            )
            router.handle_any_alert()
            try:
                ok_button = WebDriverWait(router.driver, 2).until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//button[normalize-space(text())="OK" or '
                            'normalize-space(text())="Ok" or '
                            'normalize-space(text())="Okay"]',
                        )
                    )
                )
                ok_button.click()
                logging.info("Clicked OK button on overlay.")
            except TimeoutException:
                pass
            router.handle_duplicate_overlay()
            return True
        except TimeoutException:
            if handled_alert:
                logging.info(
                    "No overlay after handling alert(s) after Ready to "
                    "Process. Returning ALERT_HANDLED to let caller decide."
                )
                return "ALERT_HANDLED"

            logging.info(
                "No popup overlay appeared after clicking Ready to "
                "Process. Proceeding."
            )
            return False
    except Exception as error:
        if ready_clicked:
            logging.warning(
                "Ready to Process was clicked, but post-click "
                "overlay/alert inspection failed; proceeding to Save. "
                "Error: %s",
                error,
            )
            return False
        logging.info(
            "Ready to Process checkbox is not clickable; treating the "
            "document as already processed."
        )
        return "READY_NOT_CLICKABLE"
