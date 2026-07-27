"""SMD/DAR related counsel LNI discovery and attachment orchestration."""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from ..smducar_config import status_updates_buffer
from ..smducar_filetypes import get_related_counsel_lnis


def handle_related_ln_is(
    router,
    row,
    full_df,
    row_index=None,
    file_path=None,
    dar_mode=False,
    wc_mode=False,
    *,
    format_docket_number,
):
    """Discover, attach, and verify related counsel LNIs."""

    try:
        main_docket = format_docket_number(
            None,
            row["FileName"],
            dar_mode,
            wc_mode,
        )
        logging.info("Processing related LNIs for docket: %s", main_docket)

        related_ln_is = get_related_counsel_lnis(
            main_docket,
            full_df,
            recycled_lni=row.get("RecycledCounselLNI"),
            dar_mode=dar_mode,
            wc_mode=wc_mode,
        )

        if not related_ln_is:
            logging.info(
                "No related LNIs found for docket: %s",
                main_docket,
            )
            if row_index is not None:
                status_updates_buffer[row_index] = "NO COUNSEL ATTACHED"
            return False

        logging.info(
            "Found %s related LNIs to process",
            len(related_ln_is),
        )

        related_lni_box = router.long_wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="relatedLni"]')
            )
        )
        existing_text = related_lni_box.text
        existing_lnis = [
            lni.strip()
            for lni in existing_text.split("\n")
            if lni.strip()
        ]

        attached_any = False
        for lni in related_ln_is:
            if not lni or str(lni).lower() == "nan":
                logging.warning("Skipping invalid Related LNI: %s", lni)
                continue

            if lni in existing_lnis:
                logging.info(
                    "%s already in Related LNI box. Skipping.",
                    lni,
                )
                continue

            success = False
            try:
                if not router.clear_and_fill_input(
                    '//*[@id="relateLNIs"]',
                    lni,
                ):
                    if row_index is not None:
                        status_updates_buffer[row_index] = (
                            "RELATED LNI FIELD LOCKED"
                        )
                    logging.warning(
                        "Related LNI input was not interactable for %s.",
                        lni,
                    )
                    return False
                router.wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, '//*[@id="AddRelated"]')
                    )
                ).click()

                def lni_in_listbox(driver):
                    current_box = driver.find_element(
                        By.XPATH,
                        '//*[@id="relatedLni"]',
                    )
                    updated_lnis = [
                        item.strip()
                        for item in current_box.text.split("\n")
                        if item.strip()
                    ]
                    return lni in updated_lnis

                router.long_wait.until(lni_in_listbox)
                logging.info(
                    "Related Counsel LNI %s added successfully.",
                    lni,
                )
                attached_any = True
                success = True
            except Exception as error:
                if "already exists" in str(error).lower():
                    logging.warning(
                        "Related Counsel LNI %s already attached. "
                        "Skipping.",
                        lni,
                    )
                    logging.info(
                        "%s already exists according to alert. "
                        "Skipping further attempts.",
                        lni,
                    )
                    success = True
                else:
                    logging.error("Failed to add LNI %s", lni)
                    if (
                        "TimeoutException" in str(type(error))
                        or "timeout" in str(error).lower()
                    ):
                        docket_number = (
                            format_docket_number(
                                None,
                                row["FileName"],
                                dar_mode,
                                wc_mode,
                            )
                            if "FileName" in row
                            else "?"
                        )
                        message = (
                            f"Oops! Related Counsel LNI {lni} for Docket "
                            f"Number {docket_number} did not attach after "
                            "5 minutes. Skipping this Main Opinion. Retry "
                            "again later."
                        )
                        logging.warning(message)
                        if router.show_error:
                            router.show_error(message)
                        if row_index is not None:
                            status_updates_buffer[row_index] = (
                                "RELATED LNI TIMEOUT"
                            )
                        return False
            if not success:
                logging.warning(
                    "Failed to attach LNI %s after waiting up to "
                    "5 minutes.",
                    lni,
                )

        related_lni_box = router.long_wait.until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="relatedLni"]')
            )
        )
        final_text = related_lni_box.text
        final_lnis = [
            lni.strip()
            for lni in final_text.split("\n")
            if lni.strip()
        ]
        if not any(lni in final_lnis for lni in related_ln_is):
            logging.warning(
                "No new LNIs were attached for docket: %s",
                main_docket,
            )
            if row_index is not None:
                status_updates_buffer[row_index] = "NO COUNSEL ATTACHED"
            return False

    except Exception:
        logging.error("Error handling related LNIs")
        if row_index is not None:
            status_updates_buffer[row_index] = "RELATED LNI ERROR"
        return False
    return True
