"""ITC Selenium form-routing flow.

The router remains the owner of duplicate detection, shared form helpers, locked
Archive inspection, field filling, and browser cleanup. This function preserves the
former CaseLawRouter method's temporary duplicate policy and route branches.
"""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..itc_extractor import ITCMetadata
from ..smducar_config import status_updates_buffer


def fill_itc_irt_form(
    router,
    row,
    row_index,
    itc_metadata: ITCMetadata,
    context_label="ITC",
):
    """Fill a single-document form using the shared ITC-style routing rules."""

    previous_archive_duplicate_mode = router._archive_duplicate_mode
    router._archive_duplicate_mode = bool(
        getattr(itc_metadata, "is_true_duplicate", False)
    )
    try:
        if not itc_metadata:
            logging.warning(
                "Skipping %s row because extracted metadata is missing.",
                context_label,
            )
            if row_index is not None:
                status_updates_buffer[row_index] = (
                    f"SKIPPED: {context_label} PDF DATA NOT FOUND"
                )
            return f"SKIPPED: {context_label} PDF DATA NOT FOUND"

        file_name = str(row.get("FileName", "")).strip()
        router.prepare_common_fields(
            file_name,
            decision_date=itc_metadata.decision_date,
            dar_mode=False,
            wc_mode=False,
            docket_override=itc_metadata.docket_number,
            court=itc_metadata.court,
        )
        router.handle_any_alert()

        if (
            getattr(itc_metadata, "is_excluded", False)
            and router.is_locked_archive_excluded_form(context_label)
        ):
            status_updates_buffer[row_index] = "ALREADY PROCESSED"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "ALREADY PROCESSED"

        if context_label == "ITC":
            fields_ok = router.handle_itc_fields(row, itc_metadata)
        else:
            fields_ok = router.handle_itc_fields(
                row,
                itc_metadata,
                context_label=context_label,
            )
        if not fields_ok:
            if row_index is not None:
                status_updates_buffer[row_index] = (
                    f"SKIPPED: {context_label} FORM FILL ERROR"
                )
            return f"SKIPPED: {context_label} FORM FILL ERROR"

        try:
            comments_field = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
            )
            route_field = router.wait.until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="route"]'))
            )
            is_excluded = bool(getattr(itc_metadata, "is_excluded", False))

            if not route_field.is_enabled() and comments_field.is_enabled():
                if is_excluded:
                    selected_route = router.get_selected_dropdown_text(route_field)
                    logging.info(
                        "Route dropdown is disabled after Source Detail Excluded; "
                        "selected route is: %s",
                        selected_route or "(blank)",
                    )
                else:
                    logging.info(
                        "Route dropdown is disabled - %s document already processed.",
                        context_label,
                    )
                    status_updates_buffer[row_index] = "ALREADY PROCESSED"
                    router.driver.close()
                    router.driver.switch_to.window(router.driver.window_handles[0])
                    return "ALREADY PROCESSED"

            if not comments_field.is_enabled() and not route_field.is_enabled():
                logging.error("%s IRT form is non-interactable.", context_label)
                status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
                router.driver.close()
                router.driver.switch_to.window(router.driver.window_handles[0])
                return "NON-INTERACTABLE IRT FORM"
        except Exception:
            logging.error(
                "Could not verify %s form interactability.",
                context_label,
            )
            status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "NON-INTERACTABLE IRT FORM"

        try:
            route_label = (
                "Archive"
                if (
                    getattr(itc_metadata, "is_true_duplicate", False)
                    or getattr(itc_metadata, "is_excluded", False)
                )
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
                logging.info("Selected %s route: %s", context_label, route_label)
                router.driver.execute_script(
                    "document.getElementById('route').dispatchEvent(new Event('change'))"
                )
                router.handle_any_alert()
            elif (
                route_label == "Archive"
                and getattr(itc_metadata, "is_excluded", False)
            ):
                selected_route = router.get_selected_dropdown_text(route_element)
                if router.dropdown_text_matches(selected_route, "Archive"):
                    logging.info(
                        "Confirmed disabled %s route dropdown is Archive for "
                        "Excluded source detail.",
                        context_label,
                    )
                else:
                    logging.warning(
                        "Disabled %s route dropdown is not Archive after Source Detail "
                        "Excluded; selected route is: %s",
                        context_label,
                        selected_route or "(blank)",
                    )
                    if not router.set_dropdown_by_visible_text(route_element, "Archive"):
                        raise Exception(
                            f"Disabled {context_label} route dropdown could not be set to Archive"
                        )
                    selected_route = router.get_selected_dropdown_text(route_element)
                    if not router.dropdown_text_matches(selected_route, "Archive"):
                        raise Exception(
                            "Disabled ITC route dropdown did not confirm Archive; "
                            f"selected route is {selected_route!r}"
                        )
                    logging.info(
                        "Set and confirmed disabled %s route dropdown is Archive for "
                        "Excluded source detail.",
                        context_label,
                    )
            else:
                raise Exception(
                    f"{context_label} route dropdown is disabled before route selection"
                )
        except Exception as e:
            logging.error(
                "Failed to select %s route before Ready to Process: %s",
                context_label,
                e,
            )
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
                "Ready to Process checkbox was not clickable for %s; "
                "marking document as ALREADY PROCESSED.",
                context_label,
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
        logging.error("Error filling %s IRT form: %s", context_label, e)
        if row_index is not None:
            status_updates_buffer[row_index] = "ERROR"
        return "ERROR"
    finally:
        router._archive_duplicate_mode = previous_archive_duplicate_mode
