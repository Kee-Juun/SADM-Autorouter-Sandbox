"""Shared router tab cleanup and focus-restoration policies."""

import logging


def close_extra_tabs_and_focus_main(
    router,
    *,
    session_lost_error_type,
):
    """Close every non-primary tab and retain primary-tab tracking."""

    try:
        handles = list(router.driver.window_handles)
        if not handles:
            raise session_lost_error_type(
                "Router browser session has no open windows."
            )

        primary_handle = (
            router._main_tab
            if getattr(router, "_main_tab", None) in handles
            else handles[0]
        )
        for handle in handles:
            if handle == primary_handle:
                continue
            try:
                router.driver.switch_to.window(handle)
                router.driver.close()
            except Exception as error:
                router._raise_if_invalid_session_error(
                    error,
                    "closing recovery tab",
                )

        router.driver.switch_to.window(primary_handle)
        router._opened_tab = None
        router._main_tab = primary_handle
        return True
    except session_lost_error_type:
        raise
    except Exception as error:
        router._raise_if_invalid_session_error(
            error,
            "focusing main tab",
        )
        logging.warning(
            "Could not fully reset browser tabs before retry: %s",
            error,
        )
        return False


def cleanup_tabs(router, opened_tab, main_tab):
    """Close one tracked form tab, restore focus, and clear tracking."""

    try:
        handles = router.driver.window_handles

        if opened_tab and opened_tab in handles:
            router.driver.switch_to.window(opened_tab)
            router.driver.close()
            logging.info("Closed IRT form tab.")

        if main_tab and main_tab in handles:
            router.driver.switch_to.window(main_tab)
            logging.info("Returned to main tab.")
        elif len(handles) > 0:
            router.driver.switch_to.window(handles[0])
            logging.info("Switched to first available tab.")

    except Exception as error:
        logging.error("Error during tab cleanup: %s", error)

    router._opened_tab = None
    router._main_tab = None
