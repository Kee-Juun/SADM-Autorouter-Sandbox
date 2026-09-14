"""MNSUTB Selenium form-routing flow.

The router object remains the owner of shared browser helpers and MNSUTB field
filling. This function preserves the former CaseLawRouter method's call order and
status strings.
"""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..mnsutb_extractor import MNSUTBMetadata
from ..smducar_config import status_updates_buffer


def fill_mnsutb_irt_form(
    router,
    row,
    row_index,
    mnsutb_metadata: MNSUTBMetadata,
):
    """Fill a MNSUTB IRT form using the existing shared router operations."""

    try:
        if not mnsutb_metadata:
            logging.warning("Skipping MNSUTB row because extracted metadata is missing.")
            if row_index is not None:
                status_updates_buffer[row_index] = "SKIPPED: MNSUTB PDF DATA NOT FOUND"
            return "SKIPPED: MNSUTB PDF DATA NOT FOUND"

        file_name = str(row.get("FileName", "")).strip()
        router.prepare_common_fields(
            file_name,
            decision_date=mnsutb_metadata.decision_date,
            dar_mode=False,
            wc_mode=False,
            docket_override=mnsutb_metadata.docket_number,
            court=None,
        )
        router.handle_any_alert()

        if not router.handle_mnsutb_fields(row, mnsutb_metadata):
            if row_index is not None:
                status_updates_buffer[row_index] = "SKIPPED: MNSUTB FORM FILL ERROR"
            return "SKIPPED: MNSUTB FORM FILL ERROR"

        try:
            comments_field = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
            )
            route_field = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="route"]'))
            )

            if not route_field.is_enabled() and comments_field.is_enabled():
                logging.info("Route dropdown is disabled - MNSUTB document already processed.")
                status_updates_buffer[row_index] = "ALREADY PROCESSED"
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return "ALREADY PROCESSED"

            if not comments_field.is_enabled() and not route_field.is_enabled():
                logging.error("MNSUTB IRT form is non-interactable.")
                status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return "NON-INTERACTABLE IRT FORM"
        except Exception:
            logging.error("Could not verify MNSUTB form interactability.")
            status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "NON-INTERACTABLE IRT FORM"

        try:
            route_element = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="route"]'))
            )
            if route_element.is_enabled():
                route_element = WebDriverWait(router.driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, '//*[@id="route"]'))
                )
                route_element.click()
                router.handle_any_alert()
                dropdown = Select(route_element)
                dropdown.select_by_visible_text("Outside Conversion")
                router.handle_any_alert()
                logging.info("Selected MNSUTB route: Outside Conversion")
                router.driver.execute_script(
                    "document.getElementById('route').dispatchEvent(new Event('change'))"
                )
                router.handle_any_alert()
            else:
                raise Exception("MNSUTB route dropdown is disabled before route selection")
        except Exception as e:
            logging.error("Failed to select MNSUTB route before Ready to Process: %s", e)
            status_updates_buffer[row_index] = "ROUTE ERROR"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "ROUTE ERROR"

        overlay_appeared = router.click_ready_checkbox_and_check_overlay(False)
        router.handle_any_alert()
        if overlay_appeared == "ROUTE_ERROR":
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "ROUTE ERROR"
        if overlay_appeared == "ALERT_HANDLED":
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "ALERT_HANDLED"
        if overlay_appeared == "READY_NOT_CLICKABLE":
            logging.info(
                "Ready to Process checkbox was not clickable for MNSUTB; "
                "marking document as ALREADY PROCESSED."
            )
            status_updates_buffer[row_index] = "ALREADY PROCESSED"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "ALREADY PROCESSED"

        return router.handle_routing_and_save(
            False,
            row_index,
            skip_route_and_ready=True,
        )
    except Exception as e:
        logging.error(f"Error in fill_mnsutb_irt_form(): {e}")
        if row_index is not None:
            status_updates_buffer[row_index] = "ERROR"
        return "ERROR"
