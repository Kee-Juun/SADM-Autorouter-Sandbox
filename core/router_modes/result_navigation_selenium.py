"""Search-result availability, selection, and window navigation."""

import logging

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def check_result_available(router):
    """Return whether an LNI result row is present."""

    try:
        router.search_wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "td.searchColumn.ChangeMouseCursorToHand",
                )
            )
        )
        return True
    except Exception as error:
        router._raise_if_invalid_session_error(
            error,
            "checking LNI search results",
        )
        logging.warning("No LNI result found")
        return False


def handle_lni_search(router, lni):
    """Search, confirm availability, and delegate result selection."""

    if not router.search_lni(lni):
        return False
    if not router.check_result_available():
        return False
    router.click_matching_result()
    return True


def _focus_new_tab(router, before_handles, main_tab):
    new_handles = set(router.driver.window_handles) - before_handles
    if not new_handles:
        return False

    new_tab = new_handles.pop()
    router.driver.switch_to.window(new_tab)
    logging.info("Switched to new tab for IRT Form.")
    router._opened_tab = new_tab
    router._main_tab = main_tab
    return True


def click_matching_result(router):
    """Open the matching result using the legacy multi-strategy sequence."""

    try:
        element = router.long_wait.until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    "td.searchColumn.ChangeMouseCursorToHand",
                )
            )
        )

        main_tab = router.driver.current_window_handle
        before_handles = set(router.driver.window_handles)

        try:
            (
                ActionChains(router.driver)
                .key_down(Keys.CONTROL)
                .click(element)
                .key_up(Keys.CONTROL)
                .perform()
            )
            WebDriverWait(router.driver, 5).until(
                lambda driver: len(driver.window_handles)
                > len(before_handles)
            )
            if _focus_new_tab(router, before_handles, main_tab):
                return
        except Exception:
            logging.warning(
                "New Tab Method 1 failed. Switching to Method 2..."
            )

        try:
            router.driver.execute_script(
                "arguments[0].dispatchEvent(new MouseEvent('click', "
                "{button: 1, bubbles: true}));",
                element,
            )
            WebDriverWait(router.driver, 5).until(
                lambda driver: len(driver.window_handles)
                > len(before_handles)
            )
            if _focus_new_tab(router, before_handles, main_tab):
                return
        except Exception:
            logging.warning(
                "New Tab Method 2 failed. Switching to Method 3..."
            )

        try:
            ActionChains(router.driver).context_click(element).perform()
            open_new_tab_option = WebDriverWait(router.driver, 3).until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[contains(text(), 'Open in new tab') or "
                        "contains(text(), 'Open link in new tab')]",
                    )
                )
            )
            open_new_tab_option.click()
            WebDriverWait(router.driver, 5).until(
                lambda driver: len(driver.window_handles)
                > len(before_handles)
            )
            if _focus_new_tab(router, before_handles, main_tab):
                return
        except Exception:
            logging.warning(
                "New Tab Method 3 failed. Switching to New Window Method..."
            )

        logging.error(
            "All new tab methods failed. Falling back to popup window logic."
        )
        element.click()
        logging.info(
            "Clicked on matching LNI result (popup window fallback)."
        )
        router._opened_tab = None
        router._main_tab = router.driver.current_window_handle

    except Exception:
        logging.error("Failed to click search result")
        if router.show_error:
            router.show_error("Failed to click search result")


def switch_to_popup_window(router):
    """Switch to the last popup handle and return the first handle."""

    try:
        router.wait.until(
            lambda driver: len(driver.window_handles) > 1
        )
        router.driver.switch_to.window(router.driver.window_handles[-1])
        logging.info("Switched to popup window.")
        return router.driver.window_handles[0]
    except Exception:
        logging.error("Failed to switch to popup window")
        if router.show_error:
            router.show_error("Failed to switch to popup window")
        return None
