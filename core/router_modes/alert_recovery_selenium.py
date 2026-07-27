"""Shared pending-alert acceptance and duplicate classification."""

import logging
import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


def handle_any_alert(
    router,
    timeout=3,
    archive_as_duplicate=None,
):
    """Accept pending alerts and delegate duplicate-overlay UI handling."""

    handled_alert, duplicate_seen = router.accept_pending_alerts(
        initial_timeout=timeout
    )
    if duplicate_seen:
        router.handle_duplicate_overlay(
            archive_as_duplicate=archive_as_duplicate
        )
    return handled_alert


def accept_pending_alerts(
    router,
    initial_timeout=3,
    followup_timeout=1,
    max_alerts=5,
):
    """Accept up to ``max_alerts`` and report handled/duplicate state."""

    handled_alert = False
    duplicate_seen = False
    timeout = initial_timeout

    for _ in range(max_alerts):
        try:
            alert = WebDriverWait(router.driver, timeout).until(
                EC.alert_is_present()
            )
            alert_text = alert.text.strip()
            alert.accept()
            logging.info("Handled alert: %s", alert_text)
            handled_alert = True
            if "duplicate document" in alert_text.lower():
                duplicate_seen = True
            time.sleep(0.25)
            timeout = followup_timeout
        except TimeoutException:
            break
        except Exception as error:
            logging.warning(
                "Could not accept pending alert cleanly: %s",
                error,
            )
            break

    return handled_alert, duplicate_seen
