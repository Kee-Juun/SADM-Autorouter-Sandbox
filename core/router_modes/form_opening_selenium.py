"""IRT form-opening and Modify retry orchestration."""

import logging

from ..smducar_config import status_updates_buffer


def open_and_process_form(
    router,
    row,
    full_df,
    row_index,
    file_path,
    retry_count=0,
    dar_mode=False,
    wc_mode=False,
    mspb_mode=False,
    mspb_metadata=None,
    itc_metadata=None,
    irsplr_metadata=None,
    ohtax0_metadata=None,
    mnsutb_metadata=None,
    mework_metadata=None,
    mosu00_metadata=None,
):
    """Open Modify mode, process the form, or perform a fresh-start retry."""

    max_modify_attempts = 3
    main_tab = getattr(
        router,
        "_main_tab",
        router.driver.current_window_handle,
    )
    opened_tab = getattr(router, "_opened_tab", None)

    found_modify = router.attempt_open_modify(row_index=row_index)

    if found_modify:
        status = router.fill_irt_form(
            row,
            full_df,
            row_index,
            file_path,
            skip_ready_check=True,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            mspb_mode=mspb_mode,
            mspb_metadata=mspb_metadata,
            itc_metadata=itc_metadata,
            irsplr_metadata=irsplr_metadata,
            ohtax0_metadata=ohtax0_metadata,
            mnsutb_metadata=mnsutb_metadata,
            **({"mework_metadata": mework_metadata} if mework_metadata is not None else {}),
            **({"mosu00_metadata": mosu00_metadata} if mosu00_metadata is not None else {}),
        )
        if status == "DONE":
            router.submit_irt_form(file_path, row_index)
            status_updates_buffer[row_index] = status

        router._cleanup_tabs(opened_tab, main_tab)
        return status

    logging.warning(
        "Modify button not found on attempt %s/%s",
        retry_count + 1,
        max_modify_attempts,
    )
    router._cleanup_tabs(opened_tab, main_tab)

    if retry_count < max_modify_attempts - 1:
        logging.info(
            "Fresh start: refreshing Search Inventory, re-searching LNI, "
            "and opening form again. Next attempt %s/%s",
            retry_count + 2,
            max_modify_attempts,
        )

        lni = str(row["LNI"]).strip()
        if not router.refresh_search_inventory_for_retry(
            reason=f"Modify button not found for LNI {lni}"
        ):
            status_updates_buffer[row_index] = (
                "ERROR: MODIFY REFRESH RETRY FAILED"
            )
            return "ERROR: MODIFY REFRESH RETRY FAILED"

        if router.handle_lni_search(lni):
            return router.open_and_process_form(
                row,
                full_df,
                row_index,
                file_path,
                retry_count=retry_count + 1,
                dar_mode=dar_mode,
                wc_mode=wc_mode,
                mspb_mode=mspb_mode,
                mspb_metadata=mspb_metadata,
                itc_metadata=itc_metadata,
                irsplr_metadata=irsplr_metadata,
                ohtax0_metadata=ohtax0_metadata,
                mnsutb_metadata=mnsutb_metadata,
                **({"mework_metadata": mework_metadata} if mework_metadata is not None else {}),
                **({"mosu00_metadata": mosu00_metadata} if mosu00_metadata is not None else {}),
            )

        logging.error(
            "Failed to re-search LNI before Modify retry %s/%s",
            retry_count + 2,
            max_modify_attempts,
        )
        status_updates_buffer[row_index] = "ERROR: LNI RE-SEARCH FAILED"
        return "ERROR: LNI RE-SEARCH FAILED"

    logging.error(
        "All 3 attempts failed for row %s. Moving on to next LNI.",
        row_index,
    )
    status_updates_buffer[row_index] = (
        "ERROR: MODIFY BUTTON NOT FOUND AFTER 3 ATTEMPTS"
    )
    return "ERROR: MODIFY BUTTON NOT FOUND AFTER 3 ATTEMPTS"
