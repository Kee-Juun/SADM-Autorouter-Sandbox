"""SMD/DAR counsel comments and main-opinion LNI composition."""

import logging
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from ..smducar_filetypes import is_counsel


def handle_counsel_fields(
    router,
    row,
    dar_mode=False,
    wc_mode=False,
    *,
    format_docket_number,
):
    """Populate counsel comments using existing router state and helpers."""

    comments_xpath = '//*[@id="comments"]'
    additional_comments = str(row.get("Comments", "")).strip()

    try:
        comments_field = router.wait.until(
            EC.presence_of_element_located((By.XPATH, comments_xpath))
        )
        existing_text = comments_field.get_attribute("value").strip()
        comment_parts = []

        file_name = str(row.get("FileName", "")).strip()
        if file_name:
            docket = format_docket_number(
                None,
                file_name,
                dar_mode,
                wc_mode,
            )
            if docket:
                main_lnis = [
                    str(candidate["LNI"]).strip()
                    for _, candidate in router.full_df.iterrows()
                    if not is_counsel(
                        str(candidate["FileName"]),
                        dar_mode,
                        wc_mode,
                    )
                    and format_docket_number(
                        None,
                        candidate["FileName"],
                        dar_mode,
                        wc_mode,
                    )
                    == docket
                ]

                attached_lnis = []
                for lni in main_lnis:
                    if lni and lni not in existing_text:
                        comment_parts.append(lni)
                        attached_lnis.append(lni)

                if attached_lnis:
                    logging.info(
                        "Auto-attached %s Main Opinion LNI(s) to comments: %s",
                        len(attached_lnis),
                        attached_lnis,
                    )
                elif any(lni in existing_text for lni in main_lnis):
                    logging.info(
                        "Auto-found Main LNI already present in comments. "
                        "Skipping."
                    )
                else:
                    logging.warning(
                        "Could not auto-find Main Opinion LNI for counsel "
                        "docket: %s",
                        docket,
                    )
            else:
                logging.warning(
                    "Could not extract docket number from counsel filename: %s",
                    file_name,
                )
        else:
            logging.warning("Could not get filename for counsel row")

        if additional_comments and additional_comments.lower() != "nan":
            comment_parts.append(additional_comments)
            logging.info(
                "Adding additional comments to counsel: %s",
                additional_comments,
            )

        if not comment_parts:
            logging.info("No new comments to add for counsel row.")
            return

        if existing_text:
            if existing_text.endswith("."):
                existing_text = existing_text[:-1].strip()
            updated_text = f"{existing_text}; {'; '.join(comment_parts)}"
        else:
            updated_text = "; ".join(comment_parts)

        max_retries = 2
        for attempt in range(max_retries):
            try:
                comments_field.clear()
                comments_field.send_keys(updated_text)
                logging.info(
                    "Updated comments field for counsel: %s",
                    updated_text,
                )

                try:
                    alert = router.driver.switch_to.alert
                    alert_text = alert.text.strip()
                    alert.accept()

                    if "duplicate document" in alert_text.lower():
                        logging.info(
                            "Duplicate alert detected during comment update. "
                            "Processing..."
                        )
                        router.handle_duplicate_lni_popup()
                        comments_field.clear()
                        comments_field.send_keys(updated_text)
                        logging.info(
                            "Retried filling comments after duplicate alert"
                        )
                except:
                    pass

                break
            except Exception:
                if attempt < max_retries - 1:
                    logging.warning(
                        "Failed to update comments on attempt %s, retrying...",
                        attempt + 1,
                    )
                    time.sleep(1)
                else:
                    logging.error(
                        "Failed to update comments after %s attempts",
                        max_retries,
                    )

    except Exception:
        logging.error("Error handling counsel comments field")
