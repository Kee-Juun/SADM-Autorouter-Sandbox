"""SMD/DAR main-opinion field composition.

Related-LNI and attachment behavior remains delegated to the router.
"""

import logging
import time

from selenium.common.exceptions import (
    TimeoutException,
    UnexpectedAlertPresentException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..smducar_config import status_updates_buffer
from ..smducar_data import resolve_source_detail


def handle_main_opinion_fields(
    router,
    row,
    full_df,
    row_index,
    file_path,
    dar_mode=False,
    wc_mode=False,
    *,
    format_docket_number,
):
    """Populate main-opinion fields using existing router dependencies."""

    case_name_xpath = '//*[@id="caseName"]'
    try:
        field = router.wait.until(
            EC.presence_of_element_located((By.XPATH, case_name_xpath))
        )
        existing_case_name = router.wait_for_existing_field_text(
            case_name_xpath, timeout=6
        )
        if existing_case_name:
            logging.info(
                "Main Opinion Case Name already present; leaving unchanged: %s",
                existing_case_name[:120],
            )
        elif field.is_enabled() and field.get_attribute("readonly") != "true":
            field.clear()
            field.send_keys("RE")
            logging.info("Main Opinion Case Name was blank; set to RE.")
        else:
            logging.info(
                "Skipped Main Opinion Case Name because it is not interactable."
            )
    except Exception:
        logging.error("Error setting case name")

    source_detail = str(row.get("SourceDetail", "")).strip()
    if source_detail and source_detail.lower() != "nan":
        try:
            resolved_source_detail = resolve_source_detail(source_detail)
            if resolved_source_detail:
                source_detail_dropdown = router.wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, '//*[@id="sourceDetails"]')
                    )
                )
                try:
                    source_detail_dropdown.click()
                    logging.info(
                        "Source Detail dropdown clicked successfully."
                    )

                    try:
                        WebDriverWait(router.driver, 2).until(
                            EC.alert_is_present()
                        )
                        alert = router.driver.switch_to.alert
                        alert_text = alert.text.strip()
                        alert.accept()
                        logging.info(
                            "Handled alert after dropdown click: %s",
                            alert_text,
                        )
                        if "duplicate document" in alert_text.lower():
                            router.handle_duplicate_lni_popup()
                    except TimeoutException:
                        pass
                except Exception:
                    logging.error(
                        "Source Detail dropdown is not clickable"
                    )
                    return

                try:
                    select = Select(source_detail_dropdown)
                    select.select_by_visible_text(resolved_source_detail)
                    logging.info(
                        "Selected Source Detail: %s",
                        resolved_source_detail,
                    )
                except UnexpectedAlertPresentException:
                    logging.warning(
                        "Unexpected alert during Source Detail selection"
                    )
                    try:
                        alert = router.driver.switch_to.alert
                        alert_text = alert.text.strip()
                        alert.accept()
                        logging.info("Handled alert: %s", alert_text)
                        if "duplicate document" in alert_text.lower():
                            router.handle_duplicate_lni_popup()
                            try:
                                related_checkbox = (
                                    router.driver.find_element(
                                        By.XPATH,
                                        '//*[@id="related"]',
                                    )
                                )
                                if not related_checkbox.is_selected():
                                    related_checkbox.click()
                                    logging.info(
                                        "Re-clicked the Related checkbox "
                                        "after alert reset."
                                    )
                            except Exception as click_error:
                                logging.warning(
                                    "Failed to re-click Related checkbox: %s",
                                    click_error,
                                )
                    except Exception as alert_error:
                        logging.warning(
                            "Failed to handle alert gracefully: %s",
                            alert_error,
                        )

                    try:
                        select = Select(source_detail_dropdown)
                        select.select_by_visible_text(
                            resolved_source_detail
                        )
                        logging.info(
                            "Retried and selected Source Detail: %s",
                            resolved_source_detail,
                        )
                    except Exception as retry_error:
                        logging.error(
                            "Retry failed after alert: %s",
                            retry_error,
                        )
                except Exception:
                    logging.error(
                        "Error selecting Source Detail value '%s'",
                        resolved_source_detail,
                    )
            else:
                logging.warning(
                    "Invalid Source Detail input: %s",
                    source_detail,
                )
        except Exception:
            logging.error("Error finding Source Detail dropdown")

    try:
        router.click_element('//*[@id="related"]', wait_time=0)
    except Exception:
        logging.error("Error ticking 'related' checkbox")

    main_docket = format_docket_number(
        None,
        row["FileName"],
        dar_mode,
        wc_mode,
    )
    related_attached = router.handle_related_ln_is(
        row,
        full_df,
        row_index=row_index,
        file_path=file_path,
        dar_mode=dar_mode,
        wc_mode=wc_mode,
    )
    if not related_attached:
        logging.error(
            "Skipping main opinion for docket %s because no related LNI "
            "could be attached.",
            main_docket,
        )
        current_status = (
            status_updates_buffer.get(row_index)
            if row_index is not None
            else None
        )
        if not current_status:
            current_status = "Missing Counsel Information"
            if row_index is not None:
                status_updates_buffer[row_index] = current_status
        router.driver.close()
        router.driver.switch_to.window(router.driver.window_handles[0])
        return current_status

    try:
        comments_field = router.wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="comments"]')
            )
        )
        route_element = router.wait.until(
            EC.presence_of_element_located((By.XPATH, '//*[@id="route"]'))
        )

        if (
            not comments_field.is_enabled()
            and not route_element.is_enabled()
        ):
            logging.error(
                "Both Comments and Route dropdown are non-interactable. "
                "Skipping Main Opinion."
            )
            status_updates_buffer[row_index] = "Non-interactable IRT Form"
            router.driver.close()
            router.driver.switch_to.window(router.driver.window_handles[0])
            return "Non-interactable IRT Form"

    except Exception:
        logging.error("Error checking Comments/Route interactability")
        status_updates_buffer[row_index] = "Non-interactable IRT Form"
        router.driver.close()
        router.driver.switch_to.window(router.driver.window_handles[0])
        return "Non-interactable IRT Form"

    additional_comments = str(row.get("Comments", "")).strip()
    if additional_comments and additional_comments.lower() != "nan":
        try:
            comments_field = router.wait.until(
                EC.presence_of_element_located(
                    (By.XPATH, '//*[@id="comments"]')
                )
            )
            existing_text = comments_field.get_attribute("value").strip()

            if existing_text:
                if existing_text.endswith("."):
                    existing_text = existing_text[:-1].strip()
                updated_text = f"{existing_text}; {additional_comments}"
            else:
                updated_text = additional_comments

            max_retries = 2
            for attempt in range(max_retries):
                try:
                    comments_field.clear()
                    comments_field.send_keys(updated_text)
                    logging.info(
                        "Updated comments field with additional comments: %s",
                        updated_text,
                    )
                    break
                except Exception:
                    if attempt < max_retries - 1:
                        logging.warning(
                            "Failed to update comments on attempt %s, "
                            "retrying...",
                            attempt + 1,
                        )
                        time.sleep(1)
                    else:
                        logging.error(
                            "Failed to update comments after %s attempts",
                            max_retries,
                        )
        except Exception:
            logging.error("Error handling additional comments")
