"""Shared SMD/DAR Selenium form-routing flow.

``CaseLawRouter.fill_irt_form`` remains the public dispatcher and error boundary.
This module owns only the shared SMD/DAR fallback sequence after specialized document
handlers have been ruled out and the legacy row preconditions have been evaluated.
"""

import datetime
import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..smducar_config import status_updates_buffer


def fill_smd_dar_irt_form(
    router,
    row,
    full_df,
    row_index,
    file_path,
    *,
    file_name,
    is_counsel_file,
    format_docket_number,
    skip_ready_check=False,
    dar_mode=False,
    wc_mode=False,
):
    """Run the existing shared SMD/DAR IRT form sequence."""

    manual_decision_raw = row.get("Decision Date")
    decision_date = None

    if (
        manual_decision_raw is not None
        and str(manual_decision_raw).strip().lower() != "nan"
    ):
        try:
            if isinstance(manual_decision_raw, (datetime.date, datetime.datetime)):
                decision_date = manual_decision_raw.strftime("%m-%d-%Y")
            else:
                decision_date = str(manual_decision_raw).strip()
            logging.info(
                "Using manual Decision Date from mapping sheet: %s",
                decision_date,
            )
        except Exception as error:
            logging.error(
                "Error normalizing manual Decision Date '%s': %s",
                manual_decision_raw,
                error,
            )

    if not decision_date and (
        manual_decision_raw is None
        or str(manual_decision_raw).strip().lower() == "nan"
        or str(manual_decision_raw).strip() == ""
    ):
        special_decision_date = None
        if is_counsel_file:
            counsel_docket = format_docket_number(
                None,
                file_name,
                dar_mode,
                wc_mode,
            )
            if counsel_docket:
                special_decision_date = router.find_main_opinion_date_for_counsel(
                    counsel_docket,
                    file_name,
                    dar_mode,
                    wc_mode,
                )
                if special_decision_date:
                    logging.info(
                        "Using Main Opinion date for counsel: %s",
                        special_decision_date,
                    )

            if not special_decision_date:
                special_decision_date = router.extract_decision_date_from_filename(
                    file_name
                )
        else:
            special_decision_date = router.extract_decision_date_from_filename(
                file_name
            )

        if special_decision_date:
            decision_date = special_decision_date
            logging.info(
                "Using Decision Date from filename extraction: %s",
                decision_date,
            )

    if not decision_date:
        decision_date = router.get_decision_date_from_received()
        if decision_date:
            logging.info(
                "Using Decision Date derived from Received Date: %s",
                decision_date,
            )

    router.prepare_common_fields(file_name, decision_date, dar_mode, wc_mode)
    router.handle_any_alert()

    max_attempts = 3 if is_counsel_file else 1
    attempts = 0

    while attempts < max_attempts:
        try:
            if is_counsel_file:
                router.handle_counsel_fields(row, dar_mode, wc_mode)
            else:
                router.handle_main_opinion_fields(
                    row,
                    full_df,
                    row_index,
                    file_path,
                    dar_mode,
                    wc_mode,
                )

            router.handle_any_alert()

            comments_field = router.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="comments"]')
                )
            )
            route_field = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="route"]'))
            )
            comments_enabled = comments_field.is_enabled()
            route_enabled = route_field.is_enabled()

            if not route_enabled and comments_enabled:
                logging.info(
                    "Route dropdown is disabled - document already processed. "
                    "Skipping Save & flagging as ALREADY PROCESSED."
                )
                status_updates_buffer[row_index] = "ALREADY PROCESSED"
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return "ALREADY PROCESSED"

            if not comments_enabled and not route_enabled:
                raise Exception("Comments AND Route are both non-interactable")

            break

        except Exception:
            attempts += 1
            logging.warning("Attempt %s: Non-interactable IRT form", attempts)
            if attempts >= max_attempts:
                label = "Non-interactable IRT Form"
                logging.error("%s. Max attempts reached.", label)
                if row_index is not None:
                    status_updates_buffer[row_index] = label.upper()
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return label.upper()

            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            router.open_lni_in_irt_tab(row)

    try:
        route_element = WebDriverWait(router.driver, 3).until(
            EC.element_to_be_clickable((By.XPATH, '//*[@id="route"]'))
        )
        route_element.click()
        router.handle_any_alert()
        dropdown = Select(route_element)
        route_label = "Archive" if is_counsel_file else "Outside Conversion"
        dropdown.select_by_visible_text(route_label)
        router.handle_any_alert()
        logging.info("Selected route: %s", route_label)
        router.driver.execute_script(
            "document.getElementById('route').dispatchEvent(new Event('change'))"
        )
        router.handle_any_alert()
    except Exception as e:
        logging.error("Failed to select route before Ready to Process: %s", e)
        status_updates_buffer[row_index] = "ROUTE ERROR"
        router.driver.close()
        router.driver.switch_to.window(router.driver.window_handles[0])
        return "ROUTE ERROR"

    overlay_appeared = router.click_ready_checkbox_and_check_overlay(
        is_counsel_file
    )
    router.handle_any_alert()
    if overlay_appeared == "ROUTE_ERROR":
        logging.info(
            "Marking as ROUTE ERROR due to route alert after Ready to Process."
        )
        router.driver.close()
        router.driver.switch_to.window(router.driver.window_handles[0])
        return "ROUTE ERROR"
    if overlay_appeared == "ALERT_HANDLED":
        logging.info(
            "Alert was handled after Ready to Process, but no overlay appeared. "
            "Not flagging as already processed. Returning ALERT_HANDLED."
        )
        router.driver.close()
        router.driver.switch_to.window(router.driver.window_handles[0])
        return "ALERT_HANDLED"
    if overlay_appeared == "READY_NOT_CLICKABLE":
        logging.info(
            "Ready to Process checkbox was not clickable; marking document as "
            "ALREADY PROCESSED."
        )
        status_updates_buffer[row_index] = "ALREADY PROCESSED"
        router.driver.close()
        router.driver.switch_to.window(router.driver.window_handles[0])
        return "ALREADY PROCESSED"

    return router.handle_routing_and_save(
        is_counsel_file,
        row_index,
        skip_route_and_ready=True,
    )
