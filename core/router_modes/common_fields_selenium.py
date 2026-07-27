"""Shared common-field preparation for all router form flows."""

import logging

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait


def prepare_common_fields(
    router,
    file_name,
    decision_date=None,
    dar_mode=False,
    wc_mode=False,
    docket_override=None,
    court=None,
    *,
    format_docket_number,
):
    """Populate the common IRT fields using the existing router helpers."""

    formatted_docket = docket_override or format_docket_number(
        None,
        file_name,
        dar_mode,
        wc_mode,
    )

    if not decision_date:
        decision_date = router.get_decision_date_from_received()

    router.safe_fill_field(
        '//*[@id="numberOfPages"]',
        "1",
        "Number of Pages",
    )
    router.safe_fill_field(
        '//*[@id="docketNumber"]',
        formatted_docket,
        "Docket Number",
    )
    router.safe_fill_field(
        '//*[@id="decisionDate"]',
        decision_date,
        "Decision Date",
    )
    if court:
        router.select_dropdown_by_visible_text_or_value(
            '//*[@id="court"]',
            court,
            "Court",
        )

    # Retained from the legacy method for strict structural compatibility.
    def select_dropdown_by_text(driver, element_id, visible_text):
        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, element_id))
            )
            select = Select(driver.find_element(By.ID, element_id))
            select.select_by_visible_text(visible_text)
            driver.execute_script(
                f"document.getElementById('{element_id}').dispatchEvent("
                "new Event('change'))"
            )
            logging.info(
                "Selected '%s' from dropdown '%s'.",
                visible_text,
                element_id,
            )
        except Exception:
            logging.error(
                "Could not select dropdown option from '%s'",
                element_id,
            )
