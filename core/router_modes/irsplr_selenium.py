"""IRSPLR Selenium form-routing flow.

The router remains the owner of shared form helpers, archive detection, field filling,
and browser cleanup. This function preserves the former CaseLawRouter method's branch
ordering, route choices, and status strings.
"""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..irsplr_extractor import IRSPLRMetadata
from ..smducar_config import status_updates_buffer


def fill_irsplr_irt_form(
    router,
    row,
    row_index,
    irsplr_metadata: IRSPLRMetadata,
):
    """Fill an IRSPLR IRT form using existing shared router operations."""

    try:
        if not irsplr_metadata:
            logging.warning("Skipping IRSPLR row because extracted metadata is missing.")
            if row_index is not None:
                status_updates_buffer[row_index] = "SKIPPED: IRSPLR PDF DATA NOT FOUND"
            return "SKIPPED: IRSPLR PDF DATA NOT FOUND"

        if getattr(irsplr_metadata, "is_text_fallback", False):
            if router.is_irt_form_already_processed("IRSPLR"):
                status_updates_buffer[row_index] = "ALREADY PROCESSED"
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return "ALREADY PROCESSED"

            logging.warning(
                "IRSPLR PDF text could not be extracted and the IRT form is not "
                "already processed; OCR support is required."
            )
            if row_index is not None:
                status_updates_buffer[row_index] = "SKIPPED: IRSPLR OCR REQUIRED"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "SKIPPED: IRSPLR OCR REQUIRED"

        file_name = str(row.get("FileName", "")).strip()
        router.prepare_common_fields(
            file_name,
            decision_date=irsplr_metadata.decision_date,
            dar_mode=False,
            wc_mode=False,
            docket_override=irsplr_metadata.docket_number,
            court=irsplr_metadata.court,
        )
        router.handle_any_alert()

        if (
            getattr(irsplr_metadata, "is_excluded", False)
            and router.is_locked_archive_excluded_form("IRSPLR")
        ):
            status_updates_buffer[row_index] = "ALREADY PROCESSED"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "ALREADY PROCESSED"

        if not router.handle_irsplr_fields(row, irsplr_metadata):
            if row_index is not None:
                status_updates_buffer[row_index] = "SKIPPED: IRSPLR FORM FILL ERROR"
            return "SKIPPED: IRSPLR FORM FILL ERROR"

        try:
            comments_field = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
            )
            route_field = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="route"]'))
            )
            is_excluded = bool(getattr(irsplr_metadata, "is_excluded", False))

            if not route_field.is_enabled() and comments_field.is_enabled():
                if is_excluded:
                    selected_route = router.get_selected_dropdown_text(route_field)
                    logging.info(
                        "Route dropdown is disabled after IRSPLR Source Detail "
                        "Excluded; selected route is: %s",
                        selected_route or "(blank)",
                    )
                else:
                    logging.info(
                        "Route dropdown is disabled - IRSPLR document already processed."
                    )
                    status_updates_buffer[row_index] = "ALREADY PROCESSED"
                    router.driver.close()
                    router.driver.switch_to.window(router.driver.window_handles[0])
                    return "ALREADY PROCESSED"

            if not comments_field.is_enabled() and not route_field.is_enabled():
                logging.error("IRSPLR IRT form is non-interactable.")
                status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return "NON-INTERACTABLE IRT FORM"
        except Exception:
            logging.error("Could not verify IRSPLR form interactability.")
            status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "NON-INTERACTABLE IRT FORM"

        try:
            route_label = (
                "Archive"
                if getattr(irsplr_metadata, "is_excluded", False)
                else "Outside Conversion"
            )
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
                dropdown.select_by_visible_text(route_label)
                router.handle_any_alert()
                logging.info(f"Selected IRSPLR route: {route_label}")
                router.driver.execute_script(
                    "document.getElementById('route').dispatchEvent(new Event('change'))"
                )
                router.handle_any_alert()
            elif route_label == "Archive":
                selected_route = router.get_selected_dropdown_text(route_element)
                if router.dropdown_text_matches(selected_route, "Archive"):
                    logging.info(
                        "Confirmed disabled IRSPLR route dropdown is Archive for "
                        "Excluded source detail."
                    )
                else:
                    logging.warning(
                        "Disabled IRSPLR route dropdown is not Archive after Source "
                        "Detail Excluded; selected route is: %s",
                        selected_route or "(blank)",
                    )
                    if not router.set_dropdown_by_visible_text(route_element, "Archive"):
                        raise Exception(
                            "Disabled IRSPLR route dropdown could not be set to Archive"
                        )
                    selected_route = router.get_selected_dropdown_text(route_element)
                    if not router.dropdown_text_matches(selected_route, "Archive"):
                        raise Exception(
                            "Disabled IRSPLR route dropdown did not confirm Archive; "
                            f"selected route is {selected_route!r}"
                        )
                    logging.info(
                        "Set and confirmed disabled IRSPLR route dropdown is Archive "
                        "for Excluded source detail."
                    )
            else:
                raise Exception(
                    "IRSPLR route dropdown is disabled before route selection"
                )
        except Exception:
            logging.error("Failed to select IRSPLR route before Ready to Process")
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
                "Ready to Process checkbox was not clickable for IRSPLR; "
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
        logging.error(f"Error in fill_irsplr_irt_form(): {e}")
        if row_index is not None:
            status_updates_buffer[row_index] = "ERROR"
        return "ERROR"
