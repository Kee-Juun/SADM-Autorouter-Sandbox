"""Duplicate-document policy and overlay UI handling."""

import logging
import time

from selenium.common.exceptions import (
    TimeoutException,
    UnexpectedAlertPresentException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def should_archive_duplicate(router, archive_as_duplicate=None):
    if archive_as_duplicate is None:
        return bool(getattr(router, "_archive_duplicate_mode", False))
    return bool(archive_as_duplicate)


def handle_duplicate_overlay(router, archive_as_duplicate=None):
    """Handle the dialog using the current route-specific policy."""

    archive_as_duplicate = router.should_archive_duplicate(
        archive_as_duplicate
    )
    for attempt in range(1, 4):
        router.accept_pending_alerts(
            initial_timeout=0.5,
            followup_timeout=1,
            max_alerts=5,
        )
        try:
            if archive_as_duplicate:
                router.click_duplicate_archive_radio(timeout=10)
            else:
                router.click_duplicate_process_radio(timeout=10)
            router.accept_pending_alerts(
                initial_timeout=0.5,
                followup_timeout=1,
                max_alerts=5,
            )
            router.click_duplicate_continue_button(timeout=10)
            router.accept_pending_alerts(
                initial_timeout=0.5,
                followup_timeout=1,
                max_alerts=5,
            )
            router.wait_for_duplicate_overlay_to_clear(timeout=15)
            return True
        except UnexpectedAlertPresentException:
            logging.info(
                "Duplicate alert interrupted overlay handling on attempt "
                "%s; accepting it and retrying.",
                attempt,
            )
            router.accept_pending_alerts(
                initial_timeout=1,
                followup_timeout=1,
                max_alerts=5,
            )
        except Exception as error:
            if attempt < 3:
                logging.info(
                    "Duplicate overlay handling attempt %s did not finish "
                    "yet: %s",
                    attempt,
                    error,
                )
                time.sleep(1)
                continue
            logging.error(
                "Failed to handle duplicate overlay: %s",
                error,
            )
            router.log_duplicate_overlay_diagnostics()
            return False

    return False


def handle_duplicate_lni_popup(router, archive_as_duplicate=None):
    try:
        try:
            WebDriverWait(router.driver, 3).until(EC.alert_is_present())
            alert = router.driver.switch_to.alert
            alert_text = alert.text.strip()
            alert.accept()
            logging.info("Accepted alert: %s", alert_text)

            if "duplicate document" not in alert_text.lower():
                logging.info(
                    "Alert was not a duplicate alert. Continuing..."
                )
                return
        except TimeoutException:
            logging.info(
                "No alert found when checking for duplicate popup."
            )

        if not router.handle_duplicate_overlay(
            archive_as_duplicate=archive_as_duplicate
        ):
            logging.info(
                "No duplicate overlay popup detected after alert."
            )
    except Exception as error:
        logging.error(
            "Failed to handle Duplicate LNI popup: %s",
            error,
        )
        try:
            alert = router.driver.switch_to.alert
            alert.accept()
            logging.info(
                "Accepted fallback alert after duplicate handling error."
            )
        except Exception:
            pass


def click_duplicate_process_radio(router, timeout=10):
    process_radio = WebDriverWait(router.driver, timeout).until(
        EC.presence_of_element_located((By.ID, "processDuplicate"))
    )
    router.driver.execute_script(
        "arguments[0].scrollIntoView({block: 'center'});",
        process_radio,
    )
    try:
        WebDriverWait(router.driver, 2).until(
            EC.element_to_be_clickable((By.ID, "processDuplicate"))
        )
        process_radio.click()
    except Exception:
        router.driver.execute_script(
            """
            arguments[0].checked = true;
            arguments[0].click();
            arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
            """,
            process_radio,
        )
    logging.info("Selected 'Process as a New Document' option.")


def click_duplicate_archive_radio(router, timeout=10):
    archive_option = router.find_duplicate_archive_option(timeout=timeout)
    try:
        clicked_radio = router.driver.execute_script(
            """
            const option = arguments[0];
            let input = null;
            if (option.matches && option.matches('input[type="radio"]')) {
                input = option;
            }
            if (!input && option.getAttribute) {
                const forId = option.getAttribute('for');
                if (forId) input = document.getElementById(forId);
            }
            if (!input && option.querySelector) {
                input = option.querySelector('input[type="radio"]');
            }
            if (!input) {
                const dialog = option.closest ? (option.closest('.ui-dialog') || document) : document;
                input = Array.from(dialog.querySelectorAll('input[type="radio"]')).find((radio) => {
                    const text = `${radio.id || ''} ${radio.name || ''} ${radio.value || ''}`;
                    return /archive/i.test(text);
                });
            }
            if (input) {
                input.scrollIntoView({block: 'center'});
                input.checked = true;
                input.click();
                input.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
            }
            option.click();
            return false;
            """,
            archive_option,
        )
        if not clicked_radio:
            router.click_duplicate_dialog_element(archive_option)
    except Exception:
        router.click_duplicate_dialog_element(archive_option)
    logging.info("Selected 'Archive as Duplicate' option.")


def find_duplicate_archive_option(router, timeout=10):
    archive_text_xpath = (
        "contains(translate(normalize-space(.), "
        "'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), "
        "'ARCHIVE AS DUPLICATE')"
    )

    def locate_option(driver):
        xpaths = [
            "//*[@id='archiveDuplicate' or @id='archiveAsDuplicate' or @id='archiveDuplicateDocument']",
            "//input[@type='radio' and (contains(translate(@id, 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ARCHIVE') or contains(translate(@value, 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ARCHIVE'))]",
            f"//label[{archive_text_xpath}]",
            f"//*[self::span or self::div or self::td][{archive_text_xpath}]",
        ]
        for xpath in xpaths:
            for option in driver.find_elements(By.XPATH, xpath):
                if option.is_displayed() and option.is_enabled():
                    return option
        return False

    return WebDriverWait(router.driver, timeout).until(locate_option)


def click_duplicate_continue_button(router, timeout=10):
    button = router.find_duplicate_continue_button(timeout=timeout)
    router.click_duplicate_dialog_element(button)
    logging.info("Clicked Continue button in Duplicate LNI dialog.")


def find_duplicate_continue_button(router, timeout=10):
    def locate_button(driver):
        xpaths = [
            "//div[contains(@class, 'ui-dialog') and not(contains(@style, 'display: none'))]//button[.//span[normalize-space()='Continue'] or normalize-space()='Continue']",
            "//button[.//span[normalize-space()='Continue'] or normalize-space()='Continue']",
            "//button[contains(normalize-space(.), 'Continue')]",
            "//div[contains(@class, 'ui-dialog-buttonpane')]//button[.//span[normalize-space()='OK' or normalize-space()='Ok' or normalize-space()='Okay'] or normalize-space()='OK' or normalize-space()='Ok' or normalize-space()='Okay']",
        ]
        for xpath in xpaths:
            for button in driver.find_elements(By.XPATH, xpath):
                if button.is_displayed() and button.is_enabled():
                    return button

        dialog_buttons = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'ui-dialog-buttonpane')]//button",
        )
        visible_buttons = [
            button
            for button in dialog_buttons
            if button.is_displayed() and button.is_enabled()
        ]
        if visible_buttons:
            return visible_buttons[0]
        return False

    return WebDriverWait(router.driver, timeout).until(locate_button)


def click_duplicate_dialog_element(router, element):
    try:
        router.driver.execute_script(
            "arguments[0].scrollIntoView({block: 'center'});",
            element,
        )
        element.click()
    except Exception:
        router.driver.execute_script("arguments[0].click();", element)


def wait_for_duplicate_overlay_to_clear(router, timeout=15):
    def duplicate_dialog_is_gone(driver):
        duplicate_dialogs = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'ui-dialog') and contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'DUPLICATE')]",
        )
        visible_duplicate_dialogs = [
            dialog
            for dialog in duplicate_dialogs
            if dialog.is_displayed()
        ]
        if visible_duplicate_dialogs:
            return False

        overlays = driver.find_elements(
            By.CLASS_NAME,
            "ui-widget-overlay",
        )
        visible_overlays = [
            overlay for overlay in overlays if overlay.is_displayed()
        ]
        if visible_overlays:
            return False

        process_radios = driver.find_elements(
            By.ID,
            "processDuplicate",
        )
        if any(
            router.element_is_inside_visible_dialog(radio)
            for radio in process_radios
        ):
            return False

        archive_radios = driver.find_elements(
            By.XPATH,
            "//*[contains(translate(@id, 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ARCHIVE') or contains(translate(@value, 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ARCHIVE')]",
        )
        if any(
            router.element_is_inside_visible_dialog(radio)
            for radio in archive_radios
        ):
            return False

        return True

    WebDriverWait(router.driver, timeout).until(
        duplicate_dialog_is_gone
    )
    logging.info("Overlay cleared. Safe to proceed.")


def element_is_inside_visible_dialog(router, element):
    try:
        return bool(
            router.driver.execute_script(
                """
                const element = arguments[0];
                const dialog = element.closest ? element.closest('.ui-dialog') : null;
                return !!(dialog && dialog.offsetParent !== null);
                """,
                element,
            )
        )
    except Exception:
        return False


def log_duplicate_overlay_diagnostics(router):
    try:
        dialogs = []
        for dialog in router.driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'ui-dialog')]",
        ):
            if dialog.is_displayed():
                dialogs.append((dialog.text or "").strip()[:500])
        overlay_count = len(
            [
                overlay
                for overlay in router.driver.find_elements(
                    By.CLASS_NAME,
                    "ui-widget-overlay",
                )
                if overlay.is_displayed()
            ]
        )
        process_count = len(
            [
                radio
                for radio in router.driver.find_elements(
                    By.ID,
                    "processDuplicate",
                )
                if radio.is_displayed()
            ]
        )
        archive_count = len(
            [
                radio
                for radio in router.driver.find_elements(
                    By.XPATH,
                    "//*[contains(translate(@id, 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ARCHIVE') or contains(translate(@value, 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'ARCHIVE')]",
                )
                if radio.is_displayed()
            ]
        )
        logging.warning(
            "Duplicate overlay diagnostics: visible_dialogs=%s "
            "visible_overlays=%s visible_processDuplicate=%s "
            "visible_archiveDuplicate=%s",
            dialogs,
            overlay_count,
            process_count,
            archive_count,
        )
    except Exception as error:
        logging.warning(
            "Could not collect duplicate overlay diagnostics: %s",
            error,
        )
