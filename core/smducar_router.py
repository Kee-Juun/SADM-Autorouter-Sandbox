import os
import base64
import datetime
import hashlib
import json
import logging
from dataclasses import replace
from pathlib import Path
import pandas as pd
import re
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
import time
import threading
from urllib.parse import parse_qs, unquote, urljoin, urlparse

# Config and logging utilities
from .smducar_config import (
    status_updates_buffer,
    mspb_metadata_buffer,
    itc_content_fingerprint_buffer,
    error_log_entries,
)

# Utils
from .smducar_utils import (
    extract_docket_number,
)

# File types
from .smducar_filetypes import (
    is_counsel,
    get_related_counsel_lnis,
)

# Data processing
from .smducar_data import (
    filter_mapping_data,
    resolve_source_detail,
)

# Selenium utilities
from .smducar_selenium import (
    retry_click,
)

from .rerun_status import (
    STATUS_NEEDS_RERUN_INTERRUPTED,
    mark_row_processing,
)

from .mspb_extractor import (
    parse_mspb_document_text,
    parse_mspb_pdf_bytes,
)

from .itc_extractor import (
    ITCMetadata,
    extract_itc_docket_from_filename,
    get_itc_court,
    is_itc_row,
    parse_itc_document_text,
    parse_itc_pdf_bytes,
)

from .irsplr_extractor import (
    IRSPLRMetadata,
    is_irsplr_row,
    parse_irsplr_document_text,
    parse_irsplr_pdf_bytes,
)

from .ohtax0_extractor import (
    OHTAX0Metadata,
    is_ohtax0_row,
    parse_ohtax0_document_text,
    parse_ohtax0_pdf_bytes,
)

from .mnsutb_extractor import (
    MNSUTBMetadata,
    is_mnsutb_row,
    parse_mnsutb_document_text,
    parse_mnsutb_pdf_bytes,
)
from .mework_extractor import MEWORKMetadata, is_mework_row
from .router_modes.handlers import (
    select_form_mode_handler,
    select_row_mode_handler,
)
from .router_modes.document_row_outcome_dispatch import (
    dispatch_document_row_outcome,
)
from .router_modes.batch_form_transition import (
    process_batch_form_transition,
)
from .router_modes.ohtax0_selenium import (
    fill_ohtax0_irt_form as run_ohtax0_irt_form,
)
from .router_modes.mnsutb_selenium import (
    fill_mnsutb_irt_form as run_mnsutb_irt_form,
)
from .router_modes.mspb_selenium import (
    fill_mspb_irt_form as run_mspb_irt_form,
)
from .router_modes.irsplr_selenium import (
    fill_irsplr_irt_form as run_irsplr_irt_form,
)
from .router_modes.itc_selenium import (
    fill_itc_irt_form as run_itc_irt_form,
)
from .router_modes.smd_dar_selenium import (
    fill_smd_dar_irt_form as run_smd_dar_irt_form,
)
from .router_modes.common_fields_selenium import (
    prepare_common_fields as run_prepare_common_fields,
)
from .router_modes.routing_save_selenium import (
    handle_routing_and_save as run_handle_routing_and_save,
)
from .router_modes.counsel_fields_selenium import (
    handle_counsel_fields as run_handle_counsel_fields,
)
from .router_modes.main_opinion_fields_selenium import (
    handle_main_opinion_fields as run_handle_main_opinion_fields,
)
from .router_modes.related_lni_selenium import (
    handle_related_ln_is as run_handle_related_ln_is,
)
from .router_modes.alert_recovery_selenium import (
    accept_pending_alerts as run_accept_pending_alerts,
    handle_any_alert as run_handle_any_alert,
)
from .router_modes.tab_lifecycle_selenium import (
    cleanup_tabs as run_cleanup_tabs,
    close_extra_tabs_and_focus_main as run_close_extra_tabs_and_focus_main,
)
from .router_modes.session_loss_policy import (
    handle_batch_session_loss as run_handle_batch_session_loss,
    is_invalid_session_error as run_is_invalid_session_error,
    mark_remaining_rows_after_router_session_loss as run_mark_remaining_rows_after_router_session_loss,
    raise_if_invalid_session_error as run_raise_if_invalid_session_error,
)
from .router_modes.modify_recovery_selenium import (
    attempt_open_modify as run_attempt_open_modify,
)
from .router_modes.search_inventory_recovery_selenium import (
    is_search_inventory_ready as run_is_search_inventory_ready,
    refresh_search_inventory_for_retry as run_refresh_search_inventory_for_retry,
)
from .router_modes.lni_search_selenium import (
    search_lni as run_search_lni,
)
from .router_modes.result_navigation_selenium import (
    check_result_available as run_check_result_available,
    click_matching_result as run_click_matching_result,
    handle_lni_search as run_handle_lni_search,
    switch_to_popup_window as run_switch_to_popup_window,
)
from .router_modes.form_opening_selenium import (
    open_and_process_form as run_open_and_process_form,
)
from .router_modes.duplicate_overlay_selenium import (
    click_duplicate_archive_radio as run_click_duplicate_archive_radio,
    click_duplicate_continue_button as run_click_duplicate_continue_button,
    click_duplicate_dialog_element as run_click_duplicate_dialog_element,
    click_duplicate_process_radio as run_click_duplicate_process_radio,
    element_is_inside_visible_dialog as run_element_is_inside_visible_dialog,
    find_duplicate_archive_option as run_find_duplicate_archive_option,
    find_duplicate_continue_button as run_find_duplicate_continue_button,
    handle_duplicate_lni_popup as run_handle_duplicate_lni_popup,
    handle_duplicate_overlay as run_handle_duplicate_overlay,
    log_duplicate_overlay_diagnostics as run_log_duplicate_overlay_diagnostics,
    should_archive_duplicate as run_should_archive_duplicate,
    wait_for_duplicate_overlay_to_clear as run_wait_for_duplicate_overlay_to_clear,
)
from .router_modes.ready_postclick_selenium import (
    click_ready_checkbox_and_check_overlay as run_click_ready_checkbox_and_check_overlay,
)
from .router_modes.mspb_batch_row import (
    process_mspb_document_row as run_process_mspb_document_row,
)
from .router_modes.ohtax0_batch_row import (
    process_ohtax0_document_row as run_process_ohtax0_document_row,
)
from .router_modes.mnsutb_batch_row import (
    process_mnsutb_document_row as run_process_mnsutb_document_row,
)
from .router_modes.mework_batch_row import (
    process_mework_document_row as run_process_mework_document_row,
)
from .router_modes.itc_batch_row import (
    process_itc_document_row as run_process_itc_document_row,
)
from .router_modes.irsplr_batch_row import (
    process_irsplr_document_row as run_process_irsplr_document_row,
)
from .router_modes.mosu00_batch_row import (
    process_mosu00_document_row as run_process_mosu00_document_row,
)
from .router_modes.document_run_dispatch import (
    dispatch_document_run as run_dispatch_document_run,
)
from .router_modes.shared_run_dispatch import (
    dispatch_shared_run as run_dispatch_shared_run,
)
from .router_modes.shared_run_finalization import (
    finalize_shared_run as run_finalize_shared_run,
)
from .router_modes.batch_policy import (
    emit_batch_progress,
)
from .router_modes.batch_throughput import (
    log_batch_throughput_summary,
)
from .router_modes.batch_row_error import (
    record_batch_row_error,
)
from .router_modes.batch_row_preflight import (
    prepare_batch_row,
)
from .router_modes.batch_row_finalization import (
    finalize_batch_row,
    log_batch_row_duration,
)
from .router_modes.mosu00_router_mixin import MOSU00RouterMixin
from .router_modes.mework_router_mixin import MEWORKRouterMixin
from .mosu00_extractor import is_mosu00_table_row


_itc_duplicate_lock = threading.Lock()


class RouterSessionLostError(RuntimeError):
    """Raised when the active Selenium browser session can no longer be used."""


class CaseLawRouter(MEWORKRouterMixin, MOSU00RouterMixin):
    def __init__(self, driver, show_error=None, set_status=None):
        self.driver = driver
        self.wait = WebDriverWait(self.driver, 60)
        self.long_wait = WebDriverWait(self.driver, 600)
        self.search_wait = WebDriverWait(self.driver, 90)
        self.show_error = show_error
        self.set_status = set_status
        self.mspb_download_dir = Path.home() / "Downloads" / "Case Law Auto-Routing Resources" / "MSPB PDF Downloads"
        self.mspb_download_dir.mkdir(parents=True, exist_ok=True)
        self.itc_download_dir = Path.home() / "Downloads" / "Case Law Auto-Routing Resources" / "ITC PDF Downloads"
        self.itc_download_dir.mkdir(parents=True, exist_ok=True)
        self.irsplr_download_dir = Path.home() / "Downloads" / "Case Law Auto-Routing Resources" / "IRSPLR PDF Downloads"
        self.irsplr_download_dir.mkdir(parents=True, exist_ok=True)
        self.ohtax0_download_dir = Path.home() / "Downloads" / "Case Law Auto-Routing Resources" / "OHTAX0 PDF Downloads"
        self.ohtax0_download_dir.mkdir(parents=True, exist_ok=True)
        self.mnsutb_download_dir = Path.home() / "Downloads" / "Case Law Auto-Routing Resources" / "MNSUTB PDF Downloads"
        self.mnsutb_download_dir.mkdir(parents=True, exist_ok=True)
        self.mework_download_dir = Path.home() / "Downloads" / "Case Law Auto-Routing Resources" / "MEWORK PDF Downloads"
        self.mework_download_dir.mkdir(parents=True, exist_ok=True)
        self.mosu00_download_dir = Path.home() / "Downloads" / "Case Law Auto-Routing Resources" / "MOSU00 HTML Downloads"
        self.mosu00_download_dir.mkdir(parents=True, exist_ok=True)
        self._archive_duplicate_mode = False
        self._irsplr_unreadable_pdf_signatures = set()

    @staticmethod
    def _is_invalid_session_error(error):
        return run_is_invalid_session_error(error)

    def _raise_if_invalid_session_error(self, error, context="browser action"):
        return run_raise_if_invalid_session_error(
            self,
            error,
            context=context,
            session_lost_error_type=RouterSessionLostError,
        )

    def _is_search_inventory_ready(self, timeout=8):
        return run_is_search_inventory_ready(self, timeout=timeout)

    def _close_extra_tabs_and_focus_main(self):
        return run_close_extra_tabs_and_focus_main(
            self,
            session_lost_error_type=RouterSessionLostError,
        )

    def refresh_search_inventory_for_retry(self, reason="recoverable form issue"):
        """Refresh back to Search Inventory so the same LNI can be retried once."""
        return run_refresh_search_inventory_for_retry(
            self,
            reason=reason,
        )

    def _should_refresh_retry_form_status(self, form_status, row_index):
        status = str(form_status or status_updates_buffer.get(row_index, "") or "").strip().upper()
        return status in {
            "NON-INTERACTABLE IRT FORM",
            "RELATED LNI ERROR",
            "RELATED LNI TIMEOUT",
            "RELATED LNI FIELD LOCKED",
            "ROUTE ERROR",
            "ROUTE_ERROR",
            "ROUTE DROPDOWN ERROR",
        }

    def _mark_remaining_rows_after_router_session_loss(self, df, current_full_index, message):
        return run_mark_remaining_rows_after_router_session_loss(
            df,
            current_full_index,
            message,
        )

    def describe_xpath(self, xpath):
        descriptions = {
            '//*[@id="related"]': 'Related checkbox',
            '//*[@id="sourceDetails"]': 'Source Detail dropdown',
            '//*[@id="add"]': 'Save button',
            '//*[@id="route"]': 'Route dropdown',
            # Add more as needed
        }
        return descriptions.get(xpath, xpath)    

    def safe_fill_field(self, xpath, value, field_name="Field"):
        try:
            value = self.normalize_irt_text(value)
            element = self.long_wait.until(EC.presence_of_element_located((By.XPATH, xpath)))

            if not element.is_enabled() or element.get_attribute("readonly") == "true":
                logging.info(f"Skipped {field_name} because it's not interactable.")
                return

            current_val = element.get_attribute("value")
            if current_val and current_val.strip() == str(value).strip():
                logging.info(f"{field_name} already set correctly. Skipping.")
                return

            # Clear and fill in one go
            element.clear()
            element.send_keys(value)
            logging.info(f"{field_name} set to: {value}")

            # Handle any popup that might have appeared immediately
            try:
                alert = self.driver.switch_to.alert
                alert_text = alert.text.strip()
                alert.accept()

                if "duplicate document" in alert_text.lower():
                    logging.info(f"Duplicate alert detected after {field_name}. Handling...")
                    self.handle_duplicate_lni_popup()
                    # If this was a comments field, retry the fill
                    if field_name == "Comments":
                        element.clear()
                        element.send_keys(value)
                        logging.info(f"Retried filling {field_name} after duplicate alert")
            except:
                pass  # No alert present, continue normally

        except Exception as e:
            logging.error(f"Error filling {field_name}")

    @staticmethod
    def normalize_irt_text(value):
        return (
            str(value or "")
            .replace("\u2010", "-")
            .replace("\u2011", "-")
            .replace("\u2012", "-")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
            .replace("\u2212", "-")
        )

    def check_session_validity(self):
        """Check if the current browser session is still valid"""
        try:
            # Try to get the current URL - this will fail if session is invalid
            current_url = self.driver.current_url
            return True
        except Exception as e:
            if self._is_invalid_session_error(e):
                logging.warning("Invalid session detected. Session may have been closed.")
                return False
            return True

    def record_mspb_metadata(self, row_index, row, lni, metadata=None, metadata_status="Attempted"):
        """Capture MSPB metadata used for the final workbook sheet."""
        if row_index is None:
            return

        existing = mspb_metadata_buffer.get(row_index, {})
        record = {
            "LNI": str(lni or existing.get("LNI", "")).strip(),
            "File Name": str(row.get("FileName", existing.get("File Name", ""))).strip(),
            "Metadata Type": existing.get("Metadata Type", "MSPB"),
            "Extracted Court Code": existing.get("Extracted Court Code", ""),
            "Extracted Docket Number": existing.get("Extracted Docket Number", ""),
            "Extracted Decision Date": existing.get("Extracted Decision Date", ""),
            "Extracted Source Detail": existing.get("Extracted Source Detail", ""),
            "Extracted Other Numbers": existing.get("Extracted Other Numbers", ""),
            "Prepared Comments": existing.get("Prepared Comments", ""),
            "Title Hint": existing.get("Title Hint", ""),
            "Route": "Outside Conversion",
            "Metadata Status": metadata_status,
        }

        if metadata:
            record.update({
                "Extracted Court Code": getattr(metadata, "court", "") or "",
                "Extracted Docket Number": getattr(metadata, "docket_number", "") or "",
                "Extracted Decision Date": getattr(metadata, "decision_date", "") or "",
                "Extracted Source Detail": getattr(metadata, "source_detail", "") or "",
                "Extracted Other Numbers": "; ".join(getattr(metadata, "other_numbers", ()) or ()),
                "Prepared Comments": getattr(metadata, "comments_text", "") or "",
                "Title Hint": getattr(metadata, "title_hint", "") or "",
                "Metadata Status": metadata_status or "Extracted",
            })

        mspb_metadata_buffer[row_index] = record

    def record_itc_metadata(self, row_index, row, lni, metadata=None, metadata_status="Attempted"):
        """Capture ITC metadata used for the final workbook sheet."""
        self.record_mspb_metadata(row_index, row, lni, metadata=metadata, metadata_status=metadata_status)
        if row_index in mspb_metadata_buffer:
            mspb_metadata_buffer[row_index]["Metadata Type"] = "ITC"
            if metadata and (getattr(metadata, "is_true_duplicate", False) or getattr(metadata, "is_excluded", False)):
                mspb_metadata_buffer[row_index]["Route"] = "Archive"
            if metadata and getattr(metadata, "is_true_duplicate", False) and not getattr(metadata, "is_excluded", False):
                duplicate_of = getattr(metadata, "duplicate_of", "") or ""
                if duplicate_of:
                    hint = mspb_metadata_buffer[row_index].get("Title Hint", "")
                    mspb_metadata_buffer[row_index]["Title Hint"] = f"{hint} | Duplicate of {duplicate_of}".strip(" |")
                duplicate_lni = getattr(metadata, "duplicate_of_lni", "") or ""
                if duplicate_lni:
                    prepared_comments = mspb_metadata_buffer[row_index].get("Prepared Comments", "") or ""
                    duplicate_comment = f"Dup of {duplicate_lni}"
                    if duplicate_comment not in prepared_comments:
                        mspb_metadata_buffer[row_index]["Prepared Comments"] = (
                            f"{prepared_comments}; {duplicate_comment}" if prepared_comments else duplicate_comment
                        )

    def record_irsplr_metadata(self, row_index, row, lni, metadata=None, metadata_status="Attempted"):
        """Capture IRSPLR metadata used for the final workbook sheet."""
        self.record_mspb_metadata(row_index, row, lni, metadata=metadata, metadata_status=metadata_status)
        if row_index in mspb_metadata_buffer:
            mspb_metadata_buffer[row_index]["Metadata Type"] = "IRSPLR"
            if metadata and getattr(metadata, "is_excluded", False):
                mspb_metadata_buffer[row_index]["Route"] = "Archive"

    def record_ohtax0_metadata(self, row_index, row, lni, metadata=None, metadata_status="Attempted"):
        """Capture OHTAX0 metadata used for the final workbook sheet."""
        self.record_mspb_metadata(row_index, row, lni, metadata=metadata, metadata_status=metadata_status)
        if row_index in mspb_metadata_buffer:
            mspb_metadata_buffer[row_index]["Metadata Type"] = "OHTAX0"
            if metadata and getattr(metadata, "is_excluded", False):
                mspb_metadata_buffer[row_index]["Route"] = "Archive"

    def record_mnsutb_metadata(self, row_index, row, lni, metadata=None, metadata_status="Attempted"):
        """Capture MNSUTB metadata used for the final workbook sheet."""
        self.record_mspb_metadata(row_index, row, lni, metadata=metadata, metadata_status=metadata_status)
        if row_index in mspb_metadata_buffer:
            mspb_metadata_buffer[row_index]["Metadata Type"] = "MNSUTB"

    def mark_itc_duplicate_status(self, row_index, row, lni, metadata: ITCMetadata):
        """Mark ITC metadata as a true duplicate when this run already saw identical PDF text."""
        if not metadata or not getattr(metadata, "content_fingerprint", ""):
            return metadata
        if getattr(metadata, "is_excluded", False):
            logging.info("ITC document is excluded; skipping duplicate classification so exclusion remains the primary route.")
            return metadata

        current_label = (
            str(row.get("FileName", "")).strip()
            or str(lni or "").strip()
            or f"row {row_index + 2 if row_index is not None else '?'}"
        )
        current_lni = str(lni or "").strip()

        with _itc_duplicate_lock:
            existing_record = itc_content_fingerprint_buffer.get(metadata.content_fingerprint)
            if existing_record:
                if isinstance(existing_record, dict):
                    existing_label = existing_record.get("label", "") or existing_record.get("lni", "")
                    existing_lni = existing_record.get("lni", "")
                else:
                    existing_label = str(existing_record)
                    existing_lni = ""
                logging.warning(
                    "Confirmed ITC true duplicate by PDF text fingerprint: %s duplicates %s",
                    current_label,
                    existing_label,
                )
                return replace(
                    metadata,
                    is_true_duplicate=True,
                    duplicate_of=existing_label,
                    duplicate_of_lni=existing_lni,
                )

            itc_content_fingerprint_buffer[metadata.content_fingerprint] = {
                "label": current_label,
                "lni": current_lni,
            }
            return metadata

    def search_lni(self, lni_value):
        return run_search_lni(
            self,
            lni_value,
            session_lost_error_type=RouterSessionLostError,
        )

    def click_search_inventory(self):
        try:
            search_button = self.search_wait.until(
                EC.element_to_be_clickable((By.XPATH, '//*[@id="menu"]/table/thead/tr/td[3]/h3/a')))
            search_button.click()
            logging.info("Clicked 'Search Inventory'.")
            return True
        except Exception as e:
            try:
                diagnostics = (
                    f"url={self.driver.current_url} title={self.driver.title} "
                    f"readyState={self.driver.execute_script('return document.readyState')}"
                )
            except Exception:
                diagnostics = "diagnostics unavailable"
            logging.error(f"Failed to click 'Search Inventory': {e} ({diagnostics})")
            return False

    def is_valid_lni(self, lni):
        pattern = r"^[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-\d{5}-\d{2}$"
        return bool(re.match(pattern, lni))

    def check_result_available(self):
        return run_check_result_available(self)

    def validate_row(self, row, row_index, file_path):
        lni = str(row["LNI"]).strip()
        if not lni:
            status_updates_buffer[row_index] = "ERROR: LNI NOT FOUND"
            return None
        if not self.is_valid_lni(lni):
            status_updates_buffer[row_index] = "ERROR: INVALID LNI FORMAT"
            return None
        return lni

    def handle_lni_search(self, lni):
        return run_handle_lni_search(self, lni)

    def extract_mspb_metadata_from_search_result(self, row, row_index=None):
        """Open the result PDF from the File Name column and parse MSPB metadata."""
        try:
            link_element = self.find_mspb_file_name_link(row)
            if link_element is None:
                logging.warning("MSPB File Name link was not found in the search results.")
                return None

            return self.open_mspb_link_and_extract_metadata(link_element)
        except Exception as e:
            logging.error(f"Error extracting MSPB metadata from PDF: {e}")
            return None

    def extract_itc_metadata_from_search_result(self, row, row_index=None):
        """Open the result PDF from the File Name column and parse ITC metadata."""
        try:
            link_element = self.find_mspb_file_name_link(row)
            if link_element is None:
                logging.warning("ITC File Name link was not found in the search results.")
                return None

            metadata = self.open_itc_link_and_extract_metadata(link_element, row)
            if metadata and getattr(metadata, "has_text_content", False):
                return metadata

            logging.warning(
                "ITC PDF metadata could not be extracted after strict filename "
                "fallback checks."
            )
            return None
        except Exception as e:
            logging.error(f"Error extracting ITC metadata from PDF: {e}")
            return None

    def build_itc_metadata_from_row(self, row):
        file_name = str(row.get("FileName", "")).strip()
        court_code = str(row.get("CourtCode", "")).strip()
        return parse_itc_document_text("", filename_hint=file_name, court_code_hint=court_code)

    def extract_irsplr_metadata_from_search_result(self, row, row_index=None):
        """Open the result PDF from the File Name column and parse IRSPLR metadata."""
        try:
            link_element = self.find_mspb_file_name_link(row)
            if link_element is None:
                logging.warning("IRSPLR File Name link was not found in the search results.")
                return None

            metadata = self.open_irsplr_link_and_extract_metadata(link_element, row)
            if metadata and getattr(metadata, "has_text_content", False):
                return metadata

            logging.warning("IRSPLR PDF did not expose readable text.")
            return None
        except Exception as e:
            logging.error(f"Error extracting IRSPLR metadata from PDF: {e}")
            return None

    def extract_ohtax0_metadata_from_search_result(self, row, row_index=None):
        """Open the result PDF from the File Name column and parse OHTAX0 metadata."""
        try:
            link_element = self.find_mspb_file_name_link(row)
            if link_element is None:
                logging.warning("OHTAX0 File Name link was not found in the search results.")
                return None

            metadata = self.open_ohtax0_link_and_extract_metadata(link_element, row)
            if metadata and getattr(metadata, "has_text_content", False):
                return metadata

            logging.warning("OHTAX0 PDF did not expose readable text.")
            return None
        except Exception as e:
            logging.error(f"Error extracting OHTAX0 metadata from PDF: {e}")
            return None

    def extract_mnsutb_metadata_from_search_result(self, row, row_index=None):
        """Open the result PDF from the File Name column and parse MNSUTB metadata."""
        try:
            link_element = self.find_mspb_file_name_link(row)
            if link_element is None:
                logging.warning("MNSUTB File Name link was not found in the search results.")
                return None

            metadata = self.open_mnsutb_link_and_extract_metadata(link_element, row)
            if metadata and getattr(metadata, "has_text_content", False):
                return metadata

            logging.warning("MNSUTB PDF did not expose readable text.")
            return None
        except Exception as e:
            logging.error(f"Error extracting MNSUTB metadata from PDF: {e}")
            return None

    def find_mspb_file_name_link(self, row):
        """Find the clickable document link under the File Name column in IRT results."""
        file_name = str(row.get("FileName", "")).strip()

        if file_name and file_name.lower() != "nan":
            for candidate in self.driver.find_elements(By.XPATH, f"//a[contains(normalize-space(.), {self.xpath_literal(file_name)})]"):
                if candidate.is_displayed():
                    return candidate

        # Prefer a link in the table column whose header says File Name.
        tables = self.driver.find_elements(By.XPATH, "//table")
        for table in tables:
            try:
                header_cells = table.find_elements(By.XPATH, ".//thead//th|.//thead//td|.//tr[1]/*")
                file_name_col = None
                for index, header in enumerate(header_cells):
                    header_text = (header.text or "").strip().lower()
                    if "file" in header_text and "name" in header_text:
                        file_name_col = index
                        break
                if file_name_col is None:
                    continue

                rows = table.find_elements(By.XPATH, ".//tbody/tr|.//tr[position()>1]")
                for result_row in rows:
                    cells = result_row.find_elements(By.XPATH, "./td|./th")
                    if len(cells) <= file_name_col:
                        continue
                    file_cell = cells[file_name_col]
                    links = file_cell.find_elements(By.XPATH, ".//a")
                    for link in links:
                        if link.is_displayed():
                            return link
                    if file_cell.is_displayed():
                        return file_cell
            except Exception:
                continue

        # Fallback: first visible PDF-looking link in the results.
        for candidate in self.driver.find_elements(By.XPATH, "//a[contains(translate(@href, 'PDF', 'pdf'), '.pdf')]"):
            if candidate.is_displayed():
                return candidate

        for candidate in self.driver.find_elements(By.XPATH, "//a[contains(translate(@href, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '.html') or contains(translate(@href, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '.htm')]"):
            if candidate.is_displayed():
                return candidate

        return None

    def open_mspb_link_and_extract_metadata(self, element):
        """Open the linked PDF in a browser tab and parse MSPB metadata from that tab."""
        main_tab = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        before_downloads = self.snapshot_mspb_downloads()
        opened_tab = None

        try:
            href = self._get_element_href(element)
            expected_filename = self.get_filename_from_document_href(href)
            self.enable_chrome_downloads()
            if href:
                target_url = urljoin(self.driver.current_url, href)
                self.enable_browser_network_capture()
                self.driver.execute_script("window.open(arguments[0], '_blank');", target_url)
            else:
                target_url = None
                self.enable_browser_network_capture()
                element.click()

            downloaded_metadata = self.wait_for_mspb_downloaded_metadata(before_downloads, expected_filename, timeout=20)
            if downloaded_metadata:
                return downloaded_metadata

            try:
                WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > len(before_handles))
                new_handles = set(self.driver.window_handles) - before_handles
                if new_handles:
                    opened_tab = new_handles.pop()
                    self.driver.switch_to.window(opened_tab)
            except TimeoutException:
                logging.info("MSPB link did not open a readable tab yet; continuing to watch for download.")

            downloaded_metadata = self.wait_for_mspb_downloaded_metadata(before_downloads, expected_filename, timeout=25)
            if downloaded_metadata:
                return downloaded_metadata

            logging.info("Opened MSPB PDF link in a browser tab.")
            metadata = self.wait_for_mspb_metadata_from_open_tab(target_url, before_downloads=before_downloads, expected_filename=expected_filename, timeout=75)
            if metadata:
                return metadata

            logging.warning("MSPB PDF tab opened, but metadata could not be extracted from the browser-rendered document.")
            return None
        except Exception as e:
            logging.warning(f"Could not read MSPB document in browser tab: {e}")
            return None
        finally:
            try:
                if opened_tab and opened_tab in self.driver.window_handles:
                    self.driver.close()
                if main_tab in self.driver.window_handles:
                    self.driver.switch_to.window(main_tab)
            except Exception:
                pass

    def open_itc_link_and_extract_metadata(self, element, row):
        """Open the linked PDF in a browser tab and parse ITC metadata from that tab."""
        main_tab = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        before_downloads = self.snapshot_itc_downloads()
        opened_tab = None
        file_name = str(row.get("FileName", "")).strip()
        court_code = str(row.get("CourtCode", "")).strip()

        try:
            href = self._get_element_href(element)
            expected_filename = self.get_filename_from_document_href(href) or file_name
            self.enable_chrome_downloads(self.itc_download_dir)
            if href:
                target_url = urljoin(self.driver.current_url, href)
                self.enable_browser_network_capture()
                self.driver.execute_script("window.open(arguments[0], '_blank');", target_url)
            else:
                target_url = None
                self.enable_browser_network_capture()
                element.click()

            downloaded_metadata = self.wait_for_itc_downloaded_metadata(
                before_downloads,
                expected_filename,
                court_code,
                timeout=20,
            )
            if downloaded_metadata:
                return downloaded_metadata

            try:
                WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > len(before_handles))
                new_handles = set(self.driver.window_handles) - before_handles
                if new_handles:
                    opened_tab = new_handles.pop()
                    self.driver.switch_to.window(opened_tab)
            except TimeoutException:
                logging.info("ITC link did not open a readable tab yet; continuing to watch for download.")

            downloaded_metadata = self.wait_for_itc_downloaded_metadata(
                before_downloads,
                expected_filename,
                court_code,
                timeout=25,
            )
            if downloaded_metadata:
                return downloaded_metadata

            logging.info("Opened ITC PDF link in a browser tab.")
            metadata = self.wait_for_itc_metadata_from_open_tab(
                target_url,
                before_downloads=before_downloads,
                expected_filename=expected_filename,
                court_code=court_code,
                timeout=45,
            )
            if metadata:
                return metadata

            logging.warning("ITC PDF tab opened, but metadata could not be extracted from the browser-rendered document.")
            return None
        except Exception as e:
            logging.warning(f"Could not read ITC document in browser tab: {e}")
            return None
        finally:
            try:
                if opened_tab and opened_tab in self.driver.window_handles:
                    self.driver.close()
                if main_tab in self.driver.window_handles:
                    self.driver.switch_to.window(main_tab)
            except Exception:
                pass

    def open_irsplr_link_and_extract_metadata(self, element, row):
        """Open the linked PDF in a browser tab and parse IRSPLR metadata from that tab."""
        main_tab = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        before_downloads = self.snapshot_irsplr_downloads()
        opened_tab = None
        file_name = str(row.get("FileName", "")).strip()
        court_code = str(row.get("CourtCode", "")).strip()

        try:
            href = self._get_element_href(element)
            expected_filename = self.get_filename_from_document_href(href) or file_name
            self.enable_chrome_downloads(self.irsplr_download_dir)
            if href:
                target_url = urljoin(self.driver.current_url, href)
                self.enable_browser_network_capture()
                self.driver.execute_script("window.open(arguments[0], '_blank');", target_url)
            else:
                target_url = None
                self.enable_browser_network_capture()
                element.click()

            downloaded_metadata = self.wait_for_irsplr_downloaded_metadata(
                before_downloads,
                expected_filename,
                court_code,
                timeout=20,
            )
            if downloaded_metadata:
                return downloaded_metadata

            try:
                WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > len(before_handles))
                new_handles = set(self.driver.window_handles) - before_handles
                if new_handles:
                    opened_tab = new_handles.pop()
                    self.driver.switch_to.window(opened_tab)
            except TimeoutException:
                logging.info("IRSPLR link did not open a readable tab yet; continuing to watch for download.")

            downloaded_metadata = self.wait_for_irsplr_downloaded_metadata(
                before_downloads,
                expected_filename,
                court_code,
                timeout=25,
            )
            if downloaded_metadata:
                return downloaded_metadata

            logging.info("Opened IRSPLR PDF link in a browser tab.")
            metadata = self.wait_for_irsplr_metadata_from_open_tab(
                target_url,
                before_downloads=before_downloads,
                expected_filename=expected_filename,
                court_code=court_code,
                timeout=45,
            )
            if metadata:
                return metadata

            logging.warning("IRSPLR PDF tab opened, but metadata could not be extracted from the browser-rendered document.")
            return None
        except Exception as e:
            logging.warning(f"Could not read IRSPLR document in browser tab: {e}")
            return None
        finally:
            try:
                if opened_tab and opened_tab in self.driver.window_handles:
                    self.driver.close()
                if main_tab in self.driver.window_handles:
                    self.driver.switch_to.window(main_tab)
            except Exception:
                pass

    def open_ohtax0_link_and_extract_metadata(self, element, row):
        """Open the linked PDF in a browser tab and parse OHTAX0 metadata from that tab."""
        main_tab = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        before_downloads = self.snapshot_ohtax0_downloads()
        opened_tab = None
        file_name = str(row.get("FileName", "")).strip()

        try:
            href = self._get_element_href(element)
            expected_filename = self.get_filename_from_document_href(href) or file_name
            self.enable_chrome_downloads(self.ohtax0_download_dir)
            if href:
                target_url = urljoin(self.driver.current_url, href)
                self.enable_browser_network_capture()
                self.driver.execute_script("window.open(arguments[0], '_blank');", target_url)
            else:
                target_url = None
                self.enable_browser_network_capture()
                element.click()

            downloaded_metadata = self.wait_for_ohtax0_downloaded_metadata(
                before_downloads,
                expected_filename,
                timeout=20,
            )
            if downloaded_metadata:
                return downloaded_metadata

            try:
                WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > len(before_handles))
                new_handles = set(self.driver.window_handles) - before_handles
                if new_handles:
                    opened_tab = new_handles.pop()
                    self.driver.switch_to.window(opened_tab)
            except TimeoutException:
                logging.info("OHTAX0 link did not open a readable tab yet; continuing to watch for download.")

            downloaded_metadata = self.wait_for_ohtax0_downloaded_metadata(
                before_downloads,
                expected_filename,
                timeout=25,
            )
            if downloaded_metadata:
                return downloaded_metadata

            logging.info("Opened OHTAX0 PDF link in a browser tab.")
            metadata = self.wait_for_ohtax0_metadata_from_open_tab(
                target_url,
                before_downloads=before_downloads,
                expected_filename=expected_filename,
                timeout=45,
            )
            if metadata:
                return metadata

            logging.warning("OHTAX0 PDF tab opened, but metadata could not be extracted from the browser-rendered document.")
            return None
        except Exception as e:
            logging.warning(f"Could not read OHTAX0 document in browser tab: {e}")
            return None
        finally:
            try:
                if opened_tab and opened_tab in self.driver.window_handles:
                    self.driver.close()
                if main_tab in self.driver.window_handles:
                    self.driver.switch_to.window(main_tab)
            except Exception:
                pass

    def open_mnsutb_link_and_extract_metadata(self, element, row):
        """Open the linked PDF in a browser tab and parse MNSUTB metadata from that tab."""
        main_tab = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        before_downloads = self.snapshot_mnsutb_downloads()
        opened_tab = None
        file_name = str(row.get("FileName", "")).strip()

        try:
            href = self._get_element_href(element)
            expected_filename = self.get_filename_from_document_href(href) or file_name
            self.enable_chrome_downloads(self.mnsutb_download_dir)
            if href:
                target_url = urljoin(self.driver.current_url, href)
                self.enable_browser_network_capture()
                self.driver.execute_script("window.open(arguments[0], '_blank');", target_url)
            else:
                target_url = None
                self.enable_browser_network_capture()
                element.click()

            downloaded_metadata = self.wait_for_mnsutb_downloaded_metadata(
                before_downloads,
                expected_filename,
                timeout=20,
            )
            if downloaded_metadata:
                return downloaded_metadata

            try:
                WebDriverWait(self.driver, 10).until(lambda d: len(d.window_handles) > len(before_handles))
                new_handles = set(self.driver.window_handles) - before_handles
                if new_handles:
                    opened_tab = new_handles.pop()
                    self.driver.switch_to.window(opened_tab)
            except TimeoutException:
                logging.info("MNSUTB link did not open a readable tab yet; continuing to watch for download.")

            downloaded_metadata = self.wait_for_mnsutb_downloaded_metadata(
                before_downloads,
                expected_filename,
                timeout=25,
            )
            if downloaded_metadata:
                return downloaded_metadata

            logging.info("Opened MNSUTB PDF link in a browser tab.")
            metadata = self.wait_for_mnsutb_metadata_from_open_tab(
                target_url,
                before_downloads=before_downloads,
                expected_filename=expected_filename,
                timeout=45,
            )
            if metadata:
                return metadata

            logging.warning("MNSUTB PDF tab opened, but metadata could not be extracted from the browser-rendered document.")
            return None
        except Exception as e:
            logging.warning(f"Could not read MNSUTB document in browser tab: {e}")
            return None
        finally:
            try:
                if opened_tab and opened_tab in self.driver.window_handles:
                    self.driver.close()
                if main_tab in self.driver.window_handles:
                    self.driver.switch_to.window(main_tab)
            except Exception:
                pass

    def wait_for_itc_metadata_from_open_tab(self, target_url=None, before_downloads=None, expected_filename=None, court_code=None, timeout=45):
        deadline = time.time() + timeout
        self._mspb_pdf_request_ids = set()
        self._mspb_pdf_checked_request_ids = set()
        last_status_log = 0

        while time.time() < deadline:
            self.wait_for_open_tab_load_state(timeout=5)

            downloaded_metadata = self.wait_for_itc_downloaded_metadata(
                before_downloads or {},
                expected_filename,
                court_code,
                timeout=1,
            )
            if downloaded_metadata:
                return downloaded_metadata

            pdf_bytes = self.get_opened_pdf_bytes_from_browser_network(target_url, timeout=1)
            if pdf_bytes:
                metadata = parse_itc_pdf_bytes(pdf_bytes, filename_hint=expected_filename, court_code_hint=court_code)
                if (
                    metadata
                    and metadata.has_text_content
                    and self.itc_metadata_matches_expected(metadata, expected_filename, court_code, "browser PDF tab")
                ):
                    self.log_itc_metadata(metadata, "browser PDF tab")
                    return metadata

            accessibility_text = self.read_open_pdf_accessibility_text()
            metadata = parse_itc_document_text(accessibility_text, filename_hint=expected_filename, court_code_hint=court_code)
            if (
                metadata
                and metadata.has_text_content
                and self.looks_like_itc_text(accessibility_text)
                and self.itc_metadata_matches_expected(metadata, expected_filename, court_code, "Chrome accessibility tree")
            ):
                self.log_itc_metadata(metadata, "Chrome accessibility tree")
                return metadata

            copied_text = self.copy_open_pdf_tab_text()
            metadata = parse_itc_document_text(copied_text, filename_hint=expected_filename, court_code_hint=court_code)
            if (
                metadata
                and metadata.has_text_content
                and self.looks_like_itc_text(copied_text)
                and self.itc_metadata_matches_expected(metadata, expected_filename, court_code, "browser PDF viewer clipboard")
            ):
                self.log_itc_metadata(metadata, "browser PDF viewer clipboard")
                return metadata

            visible_text = self.read_open_pdf_tab_text()
            metadata = parse_itc_document_text(visible_text, filename_hint=expected_filename, court_code_hint=court_code)
            if (
                metadata
                and metadata.has_text_content
                and self.looks_like_itc_text(visible_text)
                and self.itc_metadata_matches_expected(metadata, expected_filename, court_code, "browser visible text")
            ):
                self.log_itc_metadata(metadata, "browser visible text")
                return metadata

            if time.time() - last_status_log >= 10:
                logging.info("Waiting for ITC PDF tab to finish loading/expose text...")
                last_status_log = time.time()

            time.sleep(2)

        self.log_mspb_pdf_tab_diagnostics()
        return None

    def wait_for_irsplr_metadata_from_open_tab(self, target_url=None, before_downloads=None, expected_filename=None, court_code=None, timeout=45):
        deadline = time.time() + timeout
        self._mspb_pdf_request_ids = set()
        self._mspb_pdf_checked_request_ids = set()
        last_status_log = 0

        while time.time() < deadline:
            self.wait_for_open_tab_load_state(timeout=5)

            downloaded_metadata = self.wait_for_irsplr_downloaded_metadata(
                before_downloads or {},
                expected_filename,
                court_code,
                timeout=1,
            )
            if downloaded_metadata:
                return downloaded_metadata

            pdf_bytes = self.get_opened_pdf_bytes_from_browser_network(target_url, timeout=1)
            if pdf_bytes:
                pdf_signature = ("network", hashlib.sha1(pdf_bytes).hexdigest())
                if pdf_signature not in self._irsplr_unreadable_pdf_signatures:
                    metadata = parse_irsplr_pdf_bytes(pdf_bytes, filename_hint=expected_filename, court_code_hint=court_code)
                    if metadata and metadata.has_text_content:
                        self.log_irsplr_metadata(metadata, "browser PDF tab")
                        return metadata
                    self._irsplr_unreadable_pdf_signatures.add(pdf_signature)
                    logging.warning(
                        "IRSPLR browser PDF did not expose readable text; OCR support is required for image-only PDFs."
                    )

            accessibility_text = self.read_open_pdf_accessibility_text()
            if self.looks_like_irsplr_text(accessibility_text):
                metadata = parse_irsplr_document_text(accessibility_text, filename_hint=expected_filename, court_code_hint=court_code)
                if metadata and metadata.has_text_content:
                    self.log_irsplr_metadata(metadata, "Chrome accessibility tree")
                    return metadata

            copied_text = self.copy_open_pdf_tab_text()
            if self.looks_like_irsplr_text(copied_text):
                metadata = parse_irsplr_document_text(copied_text, filename_hint=expected_filename, court_code_hint=court_code)
                if metadata and metadata.has_text_content:
                    self.log_irsplr_metadata(metadata, "browser PDF viewer clipboard")
                    return metadata

            visible_text = self.read_open_pdf_tab_text()
            if self.looks_like_irsplr_text(visible_text):
                metadata = parse_irsplr_document_text(visible_text, filename_hint=expected_filename, court_code_hint=court_code)
                if metadata and metadata.has_text_content:
                    self.log_irsplr_metadata(metadata, "browser visible text")
                    return metadata

            if time.time() - last_status_log >= 10:
                logging.info("Waiting for IRSPLR PDF tab to finish loading/expose text...")
                last_status_log = time.time()

            time.sleep(2)

        self.log_mspb_pdf_tab_diagnostics("IRSPLR")
        return None

    def wait_for_ohtax0_metadata_from_open_tab(self, target_url=None, before_downloads=None, expected_filename=None, timeout=45):
        deadline = time.time() + timeout
        self._mspb_pdf_request_ids = set()
        self._mspb_pdf_checked_request_ids = set()
        last_status_log = 0

        while time.time() < deadline:
            self.wait_for_open_tab_load_state(timeout=5)

            downloaded_metadata = self.wait_for_ohtax0_downloaded_metadata(
                before_downloads or {},
                expected_filename,
                timeout=1,
            )
            if downloaded_metadata:
                return downloaded_metadata

            pdf_bytes = self.get_opened_pdf_bytes_from_browser_network(target_url, timeout=1)
            if pdf_bytes:
                metadata = parse_ohtax0_pdf_bytes(pdf_bytes, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_ohtax0_metadata(metadata, "browser PDF tab")
                    return metadata

            accessibility_text = self.read_open_pdf_accessibility_text()
            if self.looks_like_ohtax0_text(accessibility_text):
                metadata = parse_ohtax0_document_text(accessibility_text, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_ohtax0_metadata(metadata, "Chrome accessibility tree")
                    return metadata

            copied_text = self.copy_open_pdf_tab_text()
            if self.looks_like_ohtax0_text(copied_text):
                metadata = parse_ohtax0_document_text(copied_text, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_ohtax0_metadata(metadata, "browser PDF viewer clipboard")
                    return metadata

            visible_text = self.read_open_pdf_tab_text()
            if self.looks_like_ohtax0_text(visible_text):
                metadata = parse_ohtax0_document_text(visible_text, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_ohtax0_metadata(metadata, "browser visible text")
                    return metadata

            if time.time() - last_status_log >= 10:
                logging.info("Waiting for OHTAX0 PDF tab to finish loading/expose text...")
                last_status_log = time.time()

            time.sleep(2)

        self.log_mspb_pdf_tab_diagnostics("OHTAX0")
        return None

    def wait_for_mnsutb_metadata_from_open_tab(self, target_url=None, before_downloads=None, expected_filename=None, timeout=45):
        deadline = time.time() + timeout
        self._mspb_pdf_request_ids = set()
        self._mspb_pdf_checked_request_ids = set()
        last_status_log = 0

        while time.time() < deadline:
            self.wait_for_open_tab_load_state(timeout=5)

            downloaded_metadata = self.wait_for_mnsutb_downloaded_metadata(
                before_downloads or {},
                expected_filename,
                timeout=1,
            )
            if downloaded_metadata:
                return downloaded_metadata

            pdf_bytes = self.get_opened_pdf_bytes_from_browser_network(target_url, timeout=1)
            if pdf_bytes:
                metadata = parse_mnsutb_pdf_bytes(pdf_bytes, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_mnsutb_metadata(metadata, "browser PDF tab")
                    return metadata

            accessibility_text = self.read_open_pdf_accessibility_text()
            if self.looks_like_mnsutb_text(accessibility_text):
                metadata = parse_mnsutb_document_text(accessibility_text, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_mnsutb_metadata(metadata, "Chrome accessibility tree")
                    return metadata

            copied_text = self.copy_open_pdf_tab_text()
            if self.looks_like_mnsutb_text(copied_text):
                metadata = parse_mnsutb_document_text(copied_text, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_mnsutb_metadata(metadata, "browser PDF viewer clipboard")
                    return metadata

            visible_text = self.read_open_pdf_tab_text()
            if self.looks_like_mnsutb_text(visible_text):
                metadata = parse_mnsutb_document_text(visible_text, filename_hint=expected_filename)
                if metadata and metadata.has_text_content:
                    self.log_mnsutb_metadata(metadata, "browser visible text")
                    return metadata

            if time.time() - last_status_log >= 10:
                logging.info("Waiting for MNSUTB PDF tab to finish loading/expose text...")
                last_status_log = time.time()

            time.sleep(2)

        self.log_mspb_pdf_tab_diagnostics("MNSUTB")
        return None

    def wait_for_mspb_metadata_from_open_tab(self, target_url=None, before_downloads=None, expected_filename=None, timeout=75):
        """Poll an opened PDF tab until the document is loaded enough to parse."""
        deadline = time.time() + timeout
        self._mspb_pdf_request_ids = set()
        self._mspb_pdf_checked_request_ids = set()
        last_status_log = 0

        while time.time() < deadline:
            self.wait_for_open_tab_load_state(timeout=5)

            downloaded_metadata = self.wait_for_mspb_downloaded_metadata(before_downloads or {}, expected_filename, timeout=1)
            if downloaded_metadata:
                return downloaded_metadata

            pdf_bytes = self.get_opened_pdf_bytes_from_browser_network(target_url, timeout=1)
            if pdf_bytes:
                metadata = parse_mspb_pdf_bytes(pdf_bytes, filename_hint=expected_filename)
                if metadata:
                    self.log_mspb_metadata(metadata, "browser PDF tab")
                    return metadata

            accessibility_text = self.read_open_pdf_accessibility_text()
            if self.looks_like_mspb_text(accessibility_text):
                metadata = parse_mspb_document_text(accessibility_text, filename_hint=expected_filename)
                if metadata:
                    self.log_mspb_metadata(metadata, "Chrome accessibility tree")
                    return metadata

            copied_text = self.copy_open_pdf_tab_text()
            if self.looks_like_mspb_text(copied_text):
                metadata = parse_mspb_document_text(copied_text, filename_hint=expected_filename)
                if metadata:
                    self.log_mspb_metadata(metadata, "browser PDF viewer clipboard")
                    return metadata

            visible_text = self.read_open_pdf_tab_text()
            if self.looks_like_mspb_text(visible_text):
                metadata = parse_mspb_document_text(visible_text, filename_hint=expected_filename)
                if metadata:
                    self.log_mspb_metadata(metadata, "browser visible text")
                    return metadata

            if time.time() - last_status_log >= 10:
                logging.info("Waiting for MSPB PDF tab to finish loading/expose text...")
                last_status_log = time.time()

            time.sleep(2)

        self.log_mspb_pdf_tab_diagnostics()
        return None

    def wait_for_open_tab_load_state(self, timeout=5):
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") in ("interactive", "complete")
            )
        except Exception:
            pass

    def enable_chrome_downloads(self, download_dir=None):
        try:
            download_dir = Path(download_dir or self.mspb_download_dir)
            download_dir.mkdir(parents=True, exist_ok=True)
            self.driver.execute_cdp_cmd("Page.setDownloadBehavior", {
                "behavior": "allow",
                "downloadPath": str(download_dir),
            })
        except Exception as e:
            logging.info(f"Could not set Chrome download behavior for PDF: {e}")

    def snapshot_mspb_downloads(self):
        self.mspb_download_dir.mkdir(parents=True, exist_ok=True)
        snapshot = {}
        for path in self.mspb_download_dir.glob("*"):
            if path.is_file():
                try:
                    stat = path.stat()
                    snapshot[path.name.lower()] = (stat.st_mtime, stat.st_size)
                except Exception:
                    continue
        return snapshot

    def wait_for_mspb_downloaded_metadata(self, before_downloads, expected_filename=None, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            pdf_path = self.find_completed_mspb_download(before_downloads, expected_filename)
            if pdf_path:
                try:
                    metadata = parse_mspb_pdf_bytes(pdf_path.read_bytes(), filename_hint=pdf_path.name)
                    if metadata:
                        self.log_mspb_metadata(metadata, f"downloaded PDF {pdf_path.name}")
                        return metadata
                except Exception as e:
                    logging.warning(f"Downloaded MSPB PDF could not be parsed: {pdf_path} ({e})")
            time.sleep(0.5)
        return None

    def snapshot_itc_downloads(self):
        self.itc_download_dir.mkdir(parents=True, exist_ok=True)
        snapshot = {}
        for path in self.itc_download_dir.glob("*"):
            if path.is_file():
                try:
                    stat = path.stat()
                    snapshot[path.name.lower()] = (stat.st_mtime, stat.st_size)
                except Exception:
                    continue
        return snapshot

    def snapshot_irsplr_downloads(self):
        self.irsplr_download_dir.mkdir(parents=True, exist_ok=True)
        snapshot = {}
        for path in self.irsplr_download_dir.glob("*"):
            if path.is_file():
                try:
                    stat = path.stat()
                    snapshot[path.name.lower()] = (stat.st_mtime, stat.st_size)
                except Exception:
                    continue
        return snapshot

    def snapshot_ohtax0_downloads(self):
        self.ohtax0_download_dir.mkdir(parents=True, exist_ok=True)
        snapshot = {}
        for path in self.ohtax0_download_dir.glob("*"):
            if path.is_file():
                try:
                    stat = path.stat()
                    snapshot[path.name.lower()] = (stat.st_mtime, stat.st_size)
                except Exception:
                    continue
        return snapshot

    def snapshot_mnsutb_downloads(self):
        self.mnsutb_download_dir.mkdir(parents=True, exist_ok=True)
        snapshot = {}
        for path in self.mnsutb_download_dir.glob("*"):
            if path.is_file():
                try:
                    stat = path.stat()
                    snapshot[path.name.lower()] = (stat.st_mtime, stat.st_size)
                except Exception:
                    continue
        return snapshot

    def wait_for_itc_downloaded_metadata(self, before_downloads, expected_filename=None, court_code=None, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            pdf_path = self.find_completed_itc_download(before_downloads, expected_filename)
            if pdf_path:
                try:
                    metadata = parse_itc_pdf_bytes(
                        pdf_path.read_bytes(),
                        filename_hint=pdf_path.name,
                        court_code_hint=court_code,
                    )
                    if metadata and self.itc_metadata_matches_expected(metadata, expected_filename, court_code, pdf_path.name):
                        if not metadata.has_text_content:
                            logging.warning(
                                "Downloaded ITC PDF %s matched the row but did not expose readable text; "
                                "continuing with browser/OCR fallback.",
                                pdf_path.name,
                            )
                            return None
                        self.log_itc_metadata(metadata, f"downloaded PDF {pdf_path.name}")
                        return metadata
                except Exception as e:
                    logging.warning(f"Downloaded ITC PDF could not be parsed: {pdf_path} ({e})")
            time.sleep(0.5)
        return None

    def wait_for_irsplr_downloaded_metadata(self, before_downloads, expected_filename=None, court_code=None, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            pdf_path = self.find_completed_irsplr_download(before_downloads, expected_filename)
            if pdf_path:
                try:
                    stat = pdf_path.stat()
                    file_signature = ("download", str(pdf_path), stat.st_size, stat.st_mtime_ns)
                except Exception:
                    file_signature = ("download", str(pdf_path))
                if file_signature in self._irsplr_unreadable_pdf_signatures:
                    return None
                try:
                    metadata = parse_irsplr_pdf_bytes(
                        pdf_path.read_bytes(),
                        filename_hint=pdf_path.name,
                        court_code_hint=court_code,
                    )
                    if metadata and metadata.has_text_content:
                        self.log_irsplr_metadata(metadata, f"downloaded PDF {pdf_path.name}")
                        return metadata
                    self._irsplr_unreadable_pdf_signatures.add(file_signature)
                    logging.warning(
                        "Downloaded IRSPLR PDF %s did not expose readable text; OCR support is required for image-only PDFs.",
                        pdf_path.name,
                    )
                    return None
                except Exception as e:
                    self._irsplr_unreadable_pdf_signatures.add(file_signature)
                    logging.warning(f"Downloaded IRSPLR PDF could not be parsed: {pdf_path} ({e})")
            time.sleep(0.5)
        return None

    def wait_for_ohtax0_downloaded_metadata(self, before_downloads, expected_filename=None, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            pdf_path = self.find_completed_ohtax0_download(before_downloads, expected_filename)
            if pdf_path:
                try:
                    metadata = parse_ohtax0_pdf_bytes(
                        pdf_path.read_bytes(),
                        filename_hint=pdf_path.name,
                    )
                    if metadata and metadata.has_text_content:
                        self.log_ohtax0_metadata(metadata, f"downloaded PDF {pdf_path.name}")
                        return metadata
                    logging.warning("Downloaded OHTAX0 PDF %s did not expose readable text.", pdf_path.name)
                    return None
                except Exception as e:
                    logging.warning(f"Downloaded OHTAX0 PDF could not be parsed: {pdf_path} ({e})")
            time.sleep(0.5)
        return None

    def wait_for_mnsutb_downloaded_metadata(self, before_downloads, expected_filename=None, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            pdf_path = self.find_completed_mnsutb_download(before_downloads, expected_filename)
            if pdf_path:
                try:
                    metadata = parse_mnsutb_pdf_bytes(
                        pdf_path.read_bytes(),
                        filename_hint=pdf_path.name,
                    )
                    if metadata and metadata.has_text_content:
                        self.log_mnsutb_metadata(metadata, f"downloaded PDF {pdf_path.name}")
                        return metadata
                    logging.warning("Downloaded MNSUTB PDF %s did not expose readable text.", pdf_path.name)
                    return None
                except Exception as e:
                    logging.warning(f"Downloaded MNSUTB PDF could not be parsed: {pdf_path} ({e})")
            time.sleep(0.5)
        return None

    def itc_metadata_matches_expected(self, metadata, expected_filename=None, court_code=None, actual_filename=None):
        if not metadata:
            return False

        expected_court = get_itc_court(expected_filename, court_code)
        if expected_court and metadata.court != expected_court:
            logging.warning(
                "Rejected ITC metadata from %s: expected court %s but parsed %s.",
                actual_filename or expected_filename or "PDF",
                expected_court,
                metadata.court,
            )
            return False

        expected_docket = extract_itc_docket_from_filename(expected_filename)
        if expected_docket and metadata.docket_number != expected_docket:
            if getattr(metadata, "has_text_content", False):
                logging.warning(
                    "ITC metadata from %s has filename docket %s but readable PDF content parsed %s; using document content.",
                    actual_filename or expected_filename or "PDF",
                    expected_docket,
                    metadata.docket_number,
                )
                return True
            logging.warning(
                "Rejected ITC metadata from %s: expected docket %s but parsed %s.",
                actual_filename or expected_filename or "PDF",
                expected_docket,
                metadata.docket_number,
            )
            return False

        return True

    def find_completed_irsplr_download(self, before_downloads, expected_filename=None):
        expected_lower = expected_filename.lower() if expected_filename else None
        active_downloads = list(self.irsplr_download_dir.glob("*.crdownload"))
        candidates = []

        for path in self.irsplr_download_dir.glob("*.pdf"):
            try:
                stat = path.stat()
            except Exception:
                continue

            prior = before_downloads.get(path.name.lower())
            changed = prior is None or prior != (stat.st_mtime, stat.st_size)
            expected_match = self.path_matches_expected_download(path, expected_lower)
            if expected_lower and not expected_match:
                continue

            if (expected_match and changed) or (not expected_lower and changed):
                if not any(str(download).lower().startswith(str(path).lower()) for download in active_downloads):
                    candidates.append(path)

        if not candidates:
            return None

        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    def find_completed_ohtax0_download(self, before_downloads, expected_filename=None):
        expected_lower = expected_filename.lower() if expected_filename else None
        active_downloads = list(self.ohtax0_download_dir.glob("*.crdownload"))
        candidates = []

        for path in self.ohtax0_download_dir.glob("*.pdf"):
            try:
                stat = path.stat()
            except Exception:
                continue

            prior = before_downloads.get(path.name.lower())
            changed = prior is None or prior != (stat.st_mtime, stat.st_size)
            expected_match = self.path_matches_expected_download(path, expected_lower)
            if expected_lower and not expected_match:
                continue

            if (expected_match and changed) or (not expected_lower and changed):
                if not any(str(download).lower().startswith(str(path).lower()) for download in active_downloads):
                    candidates.append(path)

        if not candidates:
            return None

        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    def find_completed_mnsutb_download(self, before_downloads, expected_filename=None):
        expected_lower = expected_filename.lower() if expected_filename else None
        active_downloads = list(self.mnsutb_download_dir.glob("*.crdownload"))
        candidates = []

        for path in self.mnsutb_download_dir.glob("*.pdf"):
            try:
                stat = path.stat()
            except Exception:
                continue

            prior = before_downloads.get(path.name.lower())
            changed = prior is None or prior != (stat.st_mtime, stat.st_size)
            expected_match = self.path_matches_expected_download(path, expected_lower)
            if expected_lower and not expected_match:
                continue

            if (expected_match and changed) or (not expected_lower and changed):
                if not any(str(download).lower().startswith(str(path).lower()) for download in active_downloads):
                    candidates.append(path)

        if not candidates:
            return None

        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    def find_completed_mspb_download(self, before_downloads, expected_filename=None):
        expected_lower = expected_filename.lower() if expected_filename else None
        active_downloads = list(self.mspb_download_dir.glob("*.crdownload"))
        candidates = []

        for path in self.mspb_download_dir.glob("*.pdf"):
            try:
                stat = path.stat()
            except Exception:
                continue

            prior = before_downloads.get(path.name.lower())
            changed = prior is None or prior != (stat.st_mtime, stat.st_size)
            expected_match = expected_lower and (
                path.name.lower() == expected_lower or
                path.name.lower().startswith(Path(expected_lower).stem.lower())
            )
            if expected_match or changed:
                if not any(str(download).lower().startswith(str(path).lower()) for download in active_downloads):
                    candidates.append(path)

        if not candidates:
            return None

        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    def find_completed_itc_download(self, before_downloads, expected_filename=None):
        expected_lower = expected_filename.lower() if expected_filename else None
        active_downloads = list(self.itc_download_dir.glob("*.crdownload"))
        candidates = []

        for path in self.itc_download_dir.glob("*.pdf"):
            try:
                stat = path.stat()
            except Exception:
                continue

            prior = before_downloads.get(path.name.lower())
            changed = prior is None or prior != (stat.st_mtime, stat.st_size)
            expected_match = self.path_matches_expected_download(path, expected_lower)
            if expected_lower and not expected_match:
                continue

            if (expected_match and changed) or (not expected_lower and changed):
                if not any(str(download).lower().startswith(str(path).lower()) for download in active_downloads):
                    candidates.append(path)

        if not candidates:
            return None

        candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return candidates[0]

    @staticmethod
    def path_matches_expected_download(path, expected_lower):
        if not expected_lower:
            return False

        path_name = path.name.lower()
        path_stem = path.stem.lower()
        expected_stem = Path(expected_lower).stem.lower()
        return (
            path_name == expected_lower
            or path_stem == expected_stem
            or re.fullmatch(rf"{re.escape(expected_stem)}\s*\(\d+\)", path_stem) is not None
        )

    def get_filename_from_document_href(self, href):
        if not href:
            return None
        try:
            parsed = urlparse(href)
            values = parse_qs(parsed.query).get("fileName")
            if values:
                return unquote(values[0])
            name = Path(unquote(parsed.path)).name
            return name if name.lower().endswith((".pdf", ".htm", ".html")) else None
        except Exception:
            return None

    def enable_browser_network_capture(self):
        try:
            self.driver.execute_cdp_cmd("Network.enable", {})
            try:
                self.driver.get_log("performance")
            except Exception:
                pass
        except Exception as e:
            logging.info(f"Chrome network capture is unavailable for MSPB PDF extraction: {e}")

    def get_opened_pdf_bytes_from_browser_network(self, target_url=None, timeout=20):
        deadline = time.time() + timeout
        candidate_request_ids = getattr(self, "_mspb_pdf_request_ids", set())
        checked_request_ids = getattr(self, "_mspb_pdf_checked_request_ids", set())

        while time.time() < deadline:
            for entry in self.read_performance_log_entries():
                try:
                    message = json.loads(entry.get("message", "{}")).get("message", {})
                    method = message.get("method")
                    params = message.get("params", {})

                    if method == "Network.responseReceived":
                        response = params.get("response", {})
                        response_url = response.get("url", "")
                        mime_type = response.get("mimeType", "")
                        if self.is_mspb_pdf_response(response_url, mime_type, target_url):
                            request_id = params.get("requestId")
                            if request_id:
                                candidate_request_ids.add(request_id)

                    if method == "Network.loadingFinished":
                        request_id = params.get("requestId")
                        if request_id in candidate_request_ids and request_id not in checked_request_ids:
                            checked_request_ids.add(request_id)
                            pdf_bytes = self.get_network_response_body(request_id)
                            if self.is_pdf_bytes(pdf_bytes):
                                self._mspb_pdf_request_ids = candidate_request_ids
                                self._mspb_pdf_checked_request_ids = checked_request_ids
                                return pdf_bytes
                            if pdf_bytes:
                                logging.info("Ignoring non-PDF MSPB network response while waiting for the actual PDF.")
                except Exception:
                    continue
            time.sleep(0.5)

        self._mspb_pdf_request_ids = candidate_request_ids
        self._mspb_pdf_checked_request_ids = checked_request_ids
        return None

    def read_performance_log_entries(self):
        try:
            return self.driver.get_log("performance")
        except Exception:
            return []

    def is_mspb_pdf_response(self, response_url, mime_type, target_url=None):
        response_url_lower = (response_url or "").lower()
        mime_type_lower = (mime_type or "").lower()
        target_url_lower = (target_url or "").lower()

        if "pdf" in mime_type_lower:
            return True
        if response_url_lower.endswith(".pdf") or ".pdf" in response_url_lower:
            return True
        if "opendocumentinbrowser" in response_url_lower:
            return True
        if target_url_lower and response_url_lower == target_url_lower:
            return True
        return False

    def get_network_response_body(self, request_id):
        try:
            body = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
            raw_body = body.get("body", "")
            if body.get("base64Encoded"):
                return base64.b64decode(raw_body)
            return raw_body.encode("utf-8", errors="ignore")
        except Exception:
            return None

    @staticmethod
    def is_pdf_bytes(content):
        if not content:
            return False
        return content.lstrip().startswith(b"%PDF")

    @staticmethod
    def looks_like_mspb_text(text):
        if not text:
            return False
        text_upper = text.upper()
        return "MERIT SYSTEMS PROTECTION BOARD" in text_upper or "DOCKET NUMBER" in text_upper

    @staticmethod
    def looks_like_itc_text(text):
        if not text:
            return False
        text_upper = text.upper()
        return (
            "INTERNATIONAL TRADE COMMISSION" in text_upper
            or "INV. NO." in text_upper
            or "INVESTIGATION NO." in text_upper
            or "ORDER NO." in text_upper
        )

    @staticmethod
    def looks_like_irsplr_text(text):
        if not text:
            return False
        text_upper = text.upper()
        return (
            "INTERNAL REVENUE SERVICE" in text_upper
            or "PUBLICATION 1078" in text_upper
            or "RELEASE DATE" in text_upper
            or "UILC" in text_upper
            or "CCA_" in text_upper
        )

    @staticmethod
    def looks_like_ohtax0_text(text):
        if not text:
            return False
        text_upper = text.upper()
        return "OHIO BOARD OF TAX APPEALS" in text_upper or "CASE NO(S)" in text_upper

    @staticmethod
    def looks_like_mnsutb_text(text):
        if not text:
            return False
        text_upper = text.upper()
        return (
            "STATE OF MINNESOTA" in text_upper
            and "IN SUPREME COURT" in text_upper
            and "DATED" in text_upper
        )

    def read_open_pdf_accessibility_text(self):
        """Read text exposed through Chrome's accessibility tree, including PDF viewer text."""
        try:
            tree = self.driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
            values = []
            for node in tree.get("nodes", []):
                for key in ("name", "value", "description"):
                    payload = node.get(key)
                    if isinstance(payload, dict):
                        value = str(payload.get("value", "")).strip()
                        if value:
                            values.append(value)
            text = "\n".join(dict.fromkeys(values))
            if self.looks_like_mspb_text(text):
                logging.info("Read PDF text from Chrome accessibility tree.")
            return text
        except Exception as e:
            logging.info(f"Could not read MSPB PDF accessibility tree: {e}")
            return ""

    def copy_open_pdf_tab_text(self):
        """Copy selectable text from Chrome's PDF viewer and return it from the clipboard."""
        original_clipboard = self.read_windows_clipboard_text()
        try:
            try:
                self.driver.execute_script("window.focus();")
                body = self.driver.find_element(By.TAG_NAME, "body")
                self.click_center_of_pdf_viewer(body)
            except Exception:
                pass

            for _ in range(3):
                copied_text = ""
                try:
                    try:
                        self.driver.switch_to.active_element.send_keys(Keys.ESCAPE)
                    except Exception:
                        pass
                    self.click_center_of_pdf_viewer()
                    self.restore_windows_clipboard_text("")
                    ActionChains(self.driver) \
                        .key_down(Keys.CONTROL) \
                        .send_keys("a") \
                        .key_up(Keys.CONTROL) \
                        .pause(0.2) \
                        .key_down(Keys.CONTROL) \
                        .send_keys("c") \
                        .key_up(Keys.CONTROL) \
                        .perform()
                    time.sleep(0.8)
                    copied_text = self.read_windows_clipboard_text()
                    if self.looks_like_mspb_text(copied_text):
                        logging.info("Copied PDF text from the opened PDF tab.")
                        return copied_text
                    if copied_text:
                        logging.info(f"MSPB PDF clipboard copy did not contain expected text; copied {len(copied_text)} chars.")
                except Exception as e:
                    logging.info(f"MSPB PDF clipboard copy attempt failed: {e}")
                    time.sleep(0.5)

            return copied_text or ""
        finally:
            self.restore_windows_clipboard_text(original_clipboard)

    def click_center_of_pdf_viewer(self, element=None):
        try:
            self.driver.execute_script(
                """
                const x = Math.floor(window.innerWidth / 2);
                const y = Math.floor(window.innerHeight / 2);
                const target = document.elementFromPoint(x, y) || document.body;
                target.dispatchEvent(new MouseEvent('mousedown', {bubbles: true, clientX: x, clientY: y}));
                target.dispatchEvent(new MouseEvent('mouseup', {bubbles: true, clientX: x, clientY: y}));
                target.dispatchEvent(new MouseEvent('click', {bubbles: true, clientX: x, clientY: y}));
                if (target.focus) target.focus();
                """
            )
            time.sleep(0.2)
        except Exception:
            pass

        try:
            if element is None:
                element = self.driver.find_element(By.TAG_NAME, "body")
            ActionChains(self.driver).move_to_element(element).click().perform()
            time.sleep(0.3)
        except Exception:
            try:
                element.click()
            except Exception:
                pass

    def log_mspb_pdf_tab_diagnostics(self, context_label="MSPB"):
        try:
            current_url = self.driver.current_url
        except Exception:
            current_url = "<unavailable>"
        try:
            title = self.driver.title
        except Exception:
            title = "<unavailable>"
        try:
            ready_state = self.driver.execute_script("return document.readyState")
        except Exception:
            ready_state = "<unavailable>"
        try:
            body_text = self.driver.execute_script("return document.body ? document.body.innerText || document.body.textContent || '' : ''") or ""
        except Exception:
            body_text = ""
        try:
            dom_info = self.driver.execute_script(
                """
                const embeds = [...document.querySelectorAll('embed, iframe, pdf-viewer')]
                    .map(e => `${e.tagName}:${e.getAttribute('type') || ''}:${e.getAttribute('src') || ''}`)
                    .join(' | ');
                return embeds;
                """
            ) or ""
        except Exception:
            dom_info = ""

        logging.warning(
            "%s PDF tab diagnostics: url=%s title=%s readyState=%s bodyTextLen=%s embedded=%s",
            context_label,
            current_url,
            title,
            ready_state,
            len(body_text),
            dom_info[:500],
        )

    def read_windows_clipboard_text(self):
        try:
            import win32clipboard
            import win32con

            for _ in range(3):
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                            return win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT) or ""
                        return ""
                    finally:
                        win32clipboard.CloseClipboard()
                except Exception:
                    time.sleep(0.2)
            return ""
        except Exception:
            return ""

    def restore_windows_clipboard_text(self, text):
        try:
            import win32clipboard
            import win32con

            for _ in range(3):
                try:
                    win32clipboard.OpenClipboard()
                    try:
                        win32clipboard.EmptyClipboard()
                        if text:
                            win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
                    finally:
                        win32clipboard.CloseClipboard()
                    return
                except Exception:
                    time.sleep(0.2)
        except Exception:
            pass

    def read_open_pdf_tab_text(self):
        try:
            text = self.driver.execute_script(
                """
                const texts = [];
                const seen = new Set();
                function walk(node) {
                    if (!node || seen.has(node)) return;
                    seen.add(node);
                    if (node.nodeType === Node.TEXT_NODE) {
                        const value = (node.nodeValue || '').trim();
                        if (value) texts.push(value);
                        return;
                    }
                    if (node.innerText && node.innerText.trim()) {
                        texts.push(node.innerText.trim());
                    } else if (node.textContent && node.textContent.trim()) {
                        texts.push(node.textContent.trim());
                    }
                    if (node.shadowRoot) walk(node.shadowRoot);
                    for (const child of node.children || []) walk(child);
                }
                walk(document.documentElement);
                return [...new Set(texts)].join('\\n');
                """
            )
            return text or ""
        except Exception as e:
            logging.info(f"Could not read text from MSPB PDF tab DOM: {e}")
            return ""

    def log_mspb_metadata(self, metadata, source):
        logging.info(
            "Extracted MSPB metadata from %s: court=%s docket=%s decision_date=%s source_detail=%s",
            source,
            metadata.court,
            metadata.docket_number,
            metadata.decision_date,
            metadata.source_detail,
        )

    def log_itc_metadata(self, metadata, source):
        logging.info(
            "Extracted ITC metadata from %s: court=%s docket=%s decision_date=%s source_detail=%s other_numbers=%s",
            source,
            metadata.court,
            metadata.docket_number,
            metadata.decision_date,
            metadata.source_detail,
            "; ".join(metadata.other_numbers or ()),
        )

    def log_irsplr_metadata(self, metadata, source):
        logging.info(
            "Extracted IRSPLR metadata from %s: court=%s docket=%s decision_date=%s source_detail=%s excluded=%s",
            source,
            metadata.court,
            metadata.docket_number,
            metadata.decision_date,
            metadata.source_detail,
            getattr(metadata, "is_excluded", False),
        )

    def log_ohtax0_metadata(self, metadata, source):
        logging.info(
            "Extracted OHTAX0 metadata from %s: court=%s docket=%s decision_date=%s source_detail=%s other_numbers=%s",
            source,
            metadata.court,
            metadata.docket_number,
            metadata.decision_date,
            metadata.source_detail,
            "; ".join(metadata.other_numbers or ()),
        )

    def log_mnsutb_metadata(self, metadata, source):
        logging.info(
            "Extracted MNSUTB metadata from %s: court=%s docket=%s decision_date=%s source_detail=%s other_numbers=%s",
            source,
            metadata.court,
            metadata.docket_number,
            metadata.decision_date,
            metadata.source_detail,
            "; ".join(metadata.other_numbers or ()),
        )

    def _get_element_href(self, element):
        href = element.get_attribute("href")
        if href:
            return href
        try:
            child_link = element.find_element(By.XPATH, ".//a[@href]")
            return child_link.get_attribute("href")
        except Exception:
            return None

    @staticmethod
    def xpath_literal(value):
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ", \"'\", ".join(f"'{part}'" for part in parts) + ")"

    def open_and_process_form(self, row, full_df, row_index, file_path, retry_count=0, dar_mode=False, wc_mode=False, mspb_mode=False, mspb_metadata=None, itc_metadata=None, irsplr_metadata=None, ohtax0_metadata=None, mnsutb_metadata=None, mework_metadata=None, mosu00_metadata=None):
        return run_open_and_process_form(
            self,
            row,
            full_df,
            row_index,
            file_path,
            retry_count=retry_count,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            mspb_mode=mspb_mode,
            mspb_metadata=mspb_metadata,
            itc_metadata=itc_metadata,
            irsplr_metadata=irsplr_metadata,
            ohtax0_metadata=ohtax0_metadata,
            mnsutb_metadata=mnsutb_metadata,
            mework_metadata=mework_metadata,
            **({"mosu00_metadata": mosu00_metadata} if mosu00_metadata is not None else {}),
        )
    
    def _cleanup_tabs(self, opened_tab, main_tab):
        """Helper method to clean up tabs and return to main tab"""
        return run_cleanup_tabs(self, opened_tab, main_tab)

    def _refresh_and_retry_current_row(
        self,
        row,
        full_df,
        full_index,
        file_path,
        form_status,
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
        lni = str(row.get("LNI", "")).strip()
        logging.warning(
            f"Row {full_index + 2} hit recoverable form status '{form_status}'. "
            f"Refreshing Search Inventory and retrying LNI {lni} once."
        )

        if not self.refresh_search_inventory_for_retry(reason=form_status):
            status_updates_buffer[full_index] = "ERROR: REFRESH RETRY FAILED"
            return "ERROR: REFRESH RETRY FAILED"

        if not self.handle_lni_search(lni):
            status_updates_buffer[full_index] = "ERROR: LNI RE-SEARCH FAILED"
            return "ERROR: LNI RE-SEARCH FAILED"

        return self.open_and_process_form(
            row,
            full_df,
            full_index,
            file_path,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            mspb_mode=mspb_mode,
            mspb_metadata=mspb_metadata,
            itc_metadata=itc_metadata,
            irsplr_metadata=irsplr_metadata,
            ohtax0_metadata=ohtax0_metadata,
            mnsutb_metadata=mnsutb_metadata,
            mework_metadata=mework_metadata,
            mosu00_metadata=mosu00_metadata,
        )

    def process_batch(self, df, full_df, file_path, update_progress, batch_type, dar_mode=False, wc_mode=False, mspb_mode=False, irsplr_mode=False, ohtax0_mode=False, mnsutb_mode=False, mework_mode=False, mosu00_mode=False):
        self.safe_alert_accept()

        processed_rows = 0
        total_rows = len(df)
        batch_start_time = time.time()
        processed_count = 0
        total_duration = 0

        # Emit 0/total progress at the start so UI shows batch start immediately
        emit_batch_progress(update_progress, batch_type, 0, total_rows)

        stop_batch = False
        for full_index in df.index:
            row = df.loc[full_index]
            try:
                preflight = prepare_batch_row(
                    self,
                    row,
                    full_index,
                    file_path,
                    status_buffer=status_updates_buffer,
                    mark_processing=mark_row_processing,
                )
                if not preflight.should_process:
                    continue
                lni = preflight.lni

                # ⏱ Start timing for this LNI
                lni_start = time.time()

                mosu_dispatch_kwargs = {}
                if mosu00_mode:
                    mosu_dispatch_kwargs = {
                        "mosu00_mode": True,
                        "file_path": file_path,
                        "is_mosu00_table_row": is_mosu00_table_row,
                    }
                document_outcome = dispatch_document_row_outcome(
                    self,
                    full_index,
                    row,
                    lni,
                    mspb_mode=mspb_mode,
                    irsplr_mode=irsplr_mode,
                    ohtax0_mode=ohtax0_mode,
                    mnsutb_mode=mnsutb_mode,
                    mework_mode=mework_mode,
                    is_itc_row=is_itc_row,
                    is_irsplr_row=is_irsplr_row,
                    is_ohtax0_row=is_ohtax0_row,
                    is_mnsutb_row=is_mnsutb_row,
                    is_mework_row=is_mework_row,
                    select_handler=select_row_mode_handler,
                    **mosu_dispatch_kwargs,
                )
                if document_outcome.handled_document:
                    if not document_outcome.continue_to_form:
                        status_updates_buffer[full_index] = (
                            document_outcome.row_status
                        )
                        continue
                transition_outcome = process_batch_form_transition(
                    self,
                    row,
                    full_df,
                    full_index,
                    file_path,
                    lni,
                    document_outcome,
                    dar_mode=dar_mode,
                    wc_mode=wc_mode,
                    mspb_mode=mspb_mode,
                )

                # ⏱ End timing
                if not transition_outcome.continue_to_finalization:
                    status_updates_buffer[full_index] = (
                        transition_outcome.row_status
                    )
                    continue
                form_status = transition_outcome.form_status

                finalization = finalize_batch_row(
                    full_index,
                    lni_start,
                    form_status,
                    status_buffer=status_updates_buffer,
                    clock=time.time,
                )
                total_duration += finalization.duration
                processed_count += finalization.processed_increment

                log_batch_row_duration(
                    lni,
                    finalization.duration,
                    finalization.final_status,
                )
                if not finalization.processed_increment:
                    final_status = status_updates_buffer.get(full_index) or form_status
                    error_log_entries.append({
                        "Row": full_index + 2,
                        "LNI": row.get("LNI", ""),
                        "File Name": row.get("FileName", "") or row.get("File Name", ""),
                        "Status": final_status or "UNKNOWN",
                        "Error Message": (
                            f"Ended as {final_status or 'UNKNOWN'} during "
                            f"{batch_type} batch."
                        ),
                    })


            except RouterSessionLostError as e:
                session_loss_outcome = run_handle_batch_session_loss(
                    self,
                    df,
                    full_index,
                    row,
                    e,
                    error_log_entries,
                )
                stop_batch = session_loss_outcome.stop_batch
            except Exception as e:
                error_record_kwargs = {}
                if mework_mode:
                    error_record_kwargs["is_mework_row"] = is_mework_row
                if mosu00_mode:
                    error_record_kwargs["is_mosu00_table_row"] = is_mosu00_table_row
                record_batch_row_error(
                    self,
                    full_index,
                    row,
                    e,
                    mspb_mode=mspb_mode,
                    metadata_buffer=mspb_metadata_buffer,
                    status_buffer=status_updates_buffer,
                    error_entries=error_log_entries,
                    is_itc_row=is_itc_row,
                    is_irsplr_row=is_irsplr_row,
                    is_ohtax0_row=is_ohtax0_row,
                    is_mnsutb_row=is_mnsutb_row,
                    **error_record_kwargs,
                )
                try:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                except:
                    pass
            finally:
                # ✅ Always update progress, regardless of success or error
                processed_rows += 1
                emit_batch_progress(
                    update_progress,
                    batch_type,
                    processed_rows,
                    total_rows,
                )

        # ✅ ⏱ Final summary log: outside the loop
            if stop_batch:
                emit_batch_progress(
                    update_progress,
                    batch_type,
                    total_rows,
                    total_rows,
                )
                break

        if processed_count > 0:
            log_batch_throughput_summary(
                processed_count=processed_count,
                total_duration=total_duration,
                batch_start_time=batch_start_time,
                batch_type=batch_type,
                clock=time.time,
            )
            
        return processed_count, total_duration

    def process_mspb_document_row(
        self,
        row_handler,
        full_index,
        row,
        lni,
    ):
        return run_process_mspb_document_row(
            self,
            row_handler,
            full_index,
            row,
            lni,
        )

    def process_ohtax0_document_row(
        self,
        row_handler,
        full_index,
        row,
        lni,
    ):
        return run_process_ohtax0_document_row(
            self,
            row_handler,
            full_index,
            row,
            lni,
        )

    def process_mnsutb_document_row(
        self,
        row_handler,
        full_index,
        row,
        lni,
    ):
        return run_process_mnsutb_document_row(
            self,
            row_handler,
            full_index,
            row,
            lni,
        )

    def process_mework_document_row(
        self,
        row_handler,
        full_index,
        row,
        lni,
    ):
        return run_process_mework_document_row(
            self,
            row_handler,
            full_index,
            row,
            lni,
        )

    def process_itc_document_row(
        self,
        row_handler,
        full_index,
        row,
        lni,
    ):
        return run_process_itc_document_row(
            self,
            row_handler,
            full_index,
            row,
            lni,
        )

    def process_irsplr_document_row(
        self,
        row_handler,
        full_index,
        row,
        lni,
    ):
        return run_process_irsplr_document_row(
            self,
            row_handler,
            full_index,
            row,
            lni,
        )

    def process_mosu00_document_row(
        self, row_handler, full_index, row, lni, file_path
    ):
        return run_process_mosu00_document_row(
            self, row_handler, full_index, row, lni, file_path
        )

    def click_matching_result(self):
        return run_click_matching_result(self)

    def switch_to_popup_window(self):
        return run_switch_to_popup_window(self)

    def attempt_open_modify(self, file_path=None, row_index=None, max_attempts=3):
        return run_attempt_open_modify(
            self,
            file_path=file_path,
            row_index=row_index,
            max_attempts=max_attempts,
            session_lost_error_type=RouterSessionLostError,
        )

    def clear_and_fill_input(self, xpath, value):
        from selenium.common.exceptions import TimeoutException
        try:
            try:
                field = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            except TimeoutException:
                logging.warning(f"Field {xpath} not found after 60s. Checking for alerts/overlays...")
                # Try to handle any alerts/overlays
                try:
                    self.handle_any_alert(timeout=3)
                except Exception as e:
                    logging.info(f"No alert handled or error in handle_any_alert: {e}")
                try:
                    self.handle_duplicate_overlay()
                except Exception as e:
                    logging.info(f"No duplicate overlay handled or error in handle_duplicate_overlay: {e}")
                # Try again after handling
                try:
                    field = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                except TimeoutException:
                    logging.warning(f"Field {xpath} still not found after handling alerts. Waiting up to 300s for slow network...")
                    long_wait = WebDriverWait(self.driver, 300)
                    try:
                        field = long_wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
                    except TimeoutException:
                        logging.error(f"Field {xpath} not found after an additional 300s. Giving up.")
                        raise
            if field.is_enabled() and field.get_attribute("readonly") != "true":
                field.clear()
                field.send_keys(value)
                logging.info(f"Field at {xpath} cleared and filled with: {value}")
                return True
            else:
                logging.info(f"Field at {xpath} is not interactable. Skipping.")
                return False
        except Exception as e:
            self._raise_if_invalid_session_error(e, f"filling input {xpath}")
            logging.error(f"Error clearing and filling field at {xpath}: {e}")
            return False

    @staticmethod
    def format_docket_number(_, file_name, dar_mode=False, wc_mode=False):
        # Use the extract_docket_number function for consistent docket extraction
        extracted_docket = extract_docket_number(file_name, dar_mode, wc_mode)
        if extracted_docket:
            return extracted_docket
        
        # Fallback to original SMD logic if extract_docket_number returns None
        # First remove any numbers after "counsel" (e.g., counsel-1, counsel-2, etc.)
        file_name = re.sub(r"counsel-\d+", "counsel", str(file_name))
        # Remove date segment like _MMDDYYYY if present
        file_name = re.sub(r'_\d{8}', '', file_name)
        # Then remove all other parts to get just the docket number, preserving any appended letter
        docket = re.sub(r"LDC_SMD_|_PCQ|_E2E|counsel|\.pdf|\.docx|\.doc|\.html|\.htm|\.csv|\.txt", "", file_name)
        # Remove any trailing letter for IRT form input
        return re.sub(r"[a-z]$", "", docket)

    def get_decision_date_from_received(self):
        try:
            received_xpath = '//*[@id="receivedDateAndTime"]'
            field = self.driver.find_element(By.XPATH, received_xpath)

            # Wait up to 2 seconds for the field to have a value
            WebDriverWait(self.driver, 2).until(
                lambda d: d.find_element(By.XPATH, received_xpath).get_attribute("value").strip()
            )
            raw_text = self.driver.find_element(By.XPATH, received_xpath).get_attribute("value").strip()


            logging.info(f"Received date raw value: {raw_text}")

            # Extract and convert the date
            date_part = raw_text.split()[0]
            received_date = datetime.datetime.strptime(date_part, "%m-%d-%Y")
            decision_date = received_date - datetime.timedelta(days=1)
            return decision_date.strftime("%m-%d-%Y")

        except Exception as e:
            logging.error(f"Failed to get decision date")
            fallback_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%m-%d-%Y")
            logging.info(f"Fallback decision date used: {fallback_date}")
            return fallback_date

    @retry_click(max_attempts=1)
    def click_element(self, xpath, wait_time=5):
        try:
            if wait_time > 0:
                element = WebDriverWait(self.driver, wait_time).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
            else:
                element = self.driver.find_element(By.XPATH, xpath)
            element.click()
            logging.info(f"Clicked: {self.describe_xpath(xpath)}")
            return True
        except Exception as e:
            logging.error(f"Failed to click {xpath}")
            return False


    def click_ready_checkbox_and_check_overlay(self, is_counsel=True):
        """
        Clicks the Ready to Process checkbox, then checks for the overlay popup or alert.
        Returns True if overlay appeared, False if no overlay appeared and Save should proceed,
        'READY_NOT_CLICKABLE' only if the checkbox cannot be clicked before any Ready click succeeds,
        or 'ALERT_HANDLED' if an alert was handled but no overlay appeared (so caller can decide what to do).
        Handles both duplicate overlays, simple OK overlays, and route error alerts.
        """
        return run_click_ready_checkbox_and_check_overlay(
            self,
            is_counsel=is_counsel,
        )

    def fill_irt_form(self, row, full_df, row_index, file_path, skip_ready_check=False, dar_mode=False, wc_mode=False, mspb_mode=False, mspb_metadata=None, itc_metadata=None, irsplr_metadata=None, ohtax0_metadata=None, mnsutb_metadata=None, mework_metadata=None, mosu00_metadata=None):
        try:
            file_name = str(row["FileName"]).strip()
            is_counsel_file = is_counsel(file_name, dar_mode, wc_mode)
            lni = str(row["LNI"]).strip()

            metadata_by_mode = {
                "mspb": mspb_metadata,
                "itc": itc_metadata,
                "irsplr": irsplr_metadata,
                "ohtax0": ohtax0_metadata,
                "mnsutb": mnsutb_metadata,
                "mework": mework_metadata,
                "mosu00": mosu00_metadata,
            }
            form_handler = select_form_mode_handler(
                mspb_mode=mspb_mode,
                metadata_by_mode=metadata_by_mode,
            )
            if form_handler:
                return form_handler.fill_form(
                    self,
                    row,
                    row_index,
                    metadata_by_mode[form_handler.key],
                )

            return run_smd_dar_irt_form(
                self,
                row,
                full_df,
                row_index,
                file_path,
                file_name=file_name,
                is_counsel_file=is_counsel_file,
                format_docket_number=CaseLawRouter.format_docket_number,
                skip_ready_check=skip_ready_check,
                dar_mode=dar_mode,
                wc_mode=wc_mode,
            )
            
            
        except Exception as e:
            logging.error(f"Error in fill_irt_form(): {str(e)}")
            if row_index is not None:
                status_updates_buffer[row_index] = "ERROR"
            return "ERROR"

    def fill_mspb_irt_form(self, row, row_index, mspb_metadata):
        """Compatibility entry point for the extracted MSPB form flow."""
        return run_mspb_irt_form(self, row, row_index, mspb_metadata)

    def is_locked_archive_excluded_form(self, context_label="Document"):
        """Return True when the form already sits in a locked Excluded/Archive state."""
        try:
            source_element = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="sourceDetails"]')))
            route_element = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="route"]')))
            selected_source = self.get_selected_dropdown_text(source_element)
            selected_route = self.get_selected_dropdown_text(route_element)

            ready_clickable = True
            try:
                WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="readyToProcess"]')))
            except Exception:
                ready_clickable = False

            locked_archive_excluded = (
                self.dropdown_text_matches(selected_source, "Excluded")
                and self.dropdown_text_matches(selected_route, "Archive")
                and not route_element.is_enabled()
                and not ready_clickable
            )
            if locked_archive_excluded:
                logging.info(
                    "%s form is already locked as Source Detail Excluded / Route Archive.",
                    context_label,
                )
            return locked_archive_excluded
        except Exception as e:
            logging.debug("Could not inspect locked Excluded/Archive state for %s: %s", context_label, e)
            return False

    def is_irt_form_already_processed(self, context_label="Document"):
        """Return True when the open IRT form looks locked because it was already processed."""
        try:
            comments_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]')))
            route_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="route"]')))
            if not route_field.is_enabled() and comments_field.is_enabled():
                logging.info("%s route dropdown is disabled; treating document as ALREADY PROCESSED.", context_label)
                return True

            try:
                WebDriverWait(self.driver, 1).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="readyToProcess"]')))
            except Exception:
                logging.info("%s Ready to Process checkbox is not clickable; treating document as ALREADY PROCESSED.", context_label)
                return True
        except Exception as e:
            logging.debug("Could not inspect already-processed state for %s: %s", context_label, e)
        return False

    def fill_itc_irt_form(self, row, row_index, itc_metadata: ITCMetadata):
        """Compatibility entry point for the extracted ITC form flow."""
        return run_itc_irt_form(self, row, row_index, itc_metadata)

    def fill_irsplr_irt_form(self, row, row_index, irsplr_metadata: IRSPLRMetadata):
        """Compatibility entry point for the extracted IRSPLR form flow."""
        return run_irsplr_irt_form(self, row, row_index, irsplr_metadata)

    def fill_ohtax0_irt_form(self, row, row_index, ohtax0_metadata: OHTAX0Metadata):
        """Compatibility entry point for the extracted OHTAX0 form flow."""
        return run_ohtax0_irt_form(self, row, row_index, ohtax0_metadata)

    def fill_mnsutb_irt_form(self, row, row_index, mnsutb_metadata: MNSUTBMetadata):
        """Compatibility entry point for the extracted MNSUTB form flow."""
        return run_mnsutb_irt_form(self, row, row_index, mnsutb_metadata)

    def fill_mework_irt_form(self, row, row_index, mework_metadata: MEWORKMetadata):
        """Compatibility entry point for MEWORK's ITC-style form flow."""
        return run_itc_irt_form(
            self,
            row,
            row_index,
            mework_metadata,
            context_label="MEWORK",
        )

    def handle_itc_fields(self, row, itc_metadata: ITCMetadata, context_label="ITC"):
        try:
            case_name_xpath = '//*[@id="caseName"]'
            try:
                field = self.wait.until(EC.presence_of_element_located((By.XPATH, case_name_xpath)))
                existing_case_name = self.wait_for_existing_field_text(case_name_xpath, timeout=6)
                if existing_case_name:
                    logging.info(f"{context_label} Case Name already present; leaving unchanged: {existing_case_name[:120]}")
                else:
                    if field.is_enabled() and field.get_attribute("readonly") != "true":
                        field.clear()
                        field.send_keys("RE")
                        logging.info("%s Case Name was blank; set to RE.", context_label)
                    else:
                        logging.info("Skipped %s Case Name because it is not interactable.", context_label)
            except Exception:
                logging.error("Error setting %s case name", context_label)

            if not self.select_source_detail(itc_metadata.source_detail):
                return False

            comment_parts = []
            if itc_metadata.comments_text:
                comment_parts.append(itc_metadata.comments_text)

            duplicate_lni = getattr(itc_metadata, "duplicate_of_lni", "") or ""
            if (
                getattr(itc_metadata, "is_true_duplicate", False)
                and duplicate_lni
                and not getattr(itc_metadata, "is_excluded", False)
            ):
                comment_parts.append(f"Dup of {duplicate_lni}")

            additional_comments = str(row.get("Comments", "")).strip()
            if additional_comments and additional_comments.lower() != "nan":
                comment_parts.append(additional_comments)

            if comment_parts:
                if not self.append_comments(comment_parts, context_label):
                    return False

            return True
        except Exception as e:
            logging.error("Error handling %s fields: %s", context_label, e)
            return False

    def handle_irsplr_fields(self, row, irsplr_metadata: IRSPLRMetadata):
        try:
            case_name_xpath = '//*[@id="caseName"]'
            try:
                field = self.wait.until(EC.presence_of_element_located((By.XPATH, case_name_xpath)))
                existing_case_name = self.wait_for_existing_field_text(case_name_xpath, timeout=6)
                if existing_case_name:
                    logging.info(f"IRSPLR Case Name already present; leaving unchanged: {existing_case_name[:120]}")
                else:
                    if field.is_enabled() and field.get_attribute("readonly") != "true":
                        field.clear()
                        field.send_keys("RE")
                        logging.info("IRSPLR Case Name was blank; set to RE.")
                    else:
                        logging.info("Skipped IRSPLR Case Name because it is not interactable.")
            except Exception:
                logging.error("Error setting IRSPLR case name")

            if not self.select_source_detail(irsplr_metadata.source_detail):
                return False

            comment_parts = []
            if irsplr_metadata.comments_text:
                comment_parts.append(irsplr_metadata.comments_text)

            additional_comments = str(row.get("Comments", "")).strip()
            if additional_comments and additional_comments.lower() != "nan":
                comment_parts.append(additional_comments)

            if comment_parts:
                if not self.append_comments(comment_parts, "IRSPLR"):
                    return False

            return True
        except Exception as e:
            logging.error(f"Error handling IRSPLR fields: {e}")
            return False

    def handle_ohtax0_fields(self, row, ohtax0_metadata: OHTAX0Metadata):
        try:
            case_name_xpath = '//*[@id="caseName"]'
            try:
                field = self.wait.until(EC.presence_of_element_located((By.XPATH, case_name_xpath)))
                existing_case_name = self.wait_for_existing_field_text(case_name_xpath, timeout=6)
                if existing_case_name:
                    logging.info(f"OHTAX0 Case Name already present; leaving unchanged: {existing_case_name[:120]}")
                else:
                    if field.is_enabled() and field.get_attribute("readonly") != "true":
                        field.clear()
                        field.send_keys("RE")
                        logging.info("OHTAX0 Case Name was blank; set to RE.")
                    else:
                        logging.info("Skipped OHTAX0 Case Name because it is not interactable.")
            except Exception:
                logging.error("Error setting OHTAX0 case name")

            if not self.select_source_detail(ohtax0_metadata.source_detail):
                return False

            comment_parts = []
            if ohtax0_metadata.comments_text:
                comment_parts.append(ohtax0_metadata.comments_text)

            additional_comments = str(row.get("Comments", "")).strip()
            if additional_comments and additional_comments.lower() != "nan":
                comment_parts.append(additional_comments)

            if comment_parts:
                if not self.append_comments(comment_parts, "OHTAX0"):
                    return False

            return True
        except Exception as e:
            logging.error(f"Error handling OHTAX0 fields: {e}")
            return False

    def handle_mnsutb_fields(self, row, mnsutb_metadata: MNSUTBMetadata):
        try:
            case_name_xpath = '//*[@id="caseName"]'
            try:
                field = self.wait.until(EC.presence_of_element_located((By.XPATH, case_name_xpath)))
                existing_case_name = self.wait_for_existing_field_text(case_name_xpath, timeout=6)
                if existing_case_name:
                    logging.info(f"MNSUTB Case Name already present; leaving unchanged: {existing_case_name[:120]}")
                else:
                    if field.is_enabled() and field.get_attribute("readonly") != "true":
                        field.clear()
                        field.send_keys("RE")
                        logging.info("MNSUTB Case Name was blank; set to RE.")
                    else:
                        logging.info("Skipped MNSUTB Case Name because it is not interactable.")
            except Exception:
                logging.error("Error setting MNSUTB case name")

            if not self.select_source_detail(mnsutb_metadata.source_detail):
                return False

            comment_parts = []
            if mnsutb_metadata.comments_text:
                comment_parts.append(mnsutb_metadata.comments_text)

            additional_comments = str(row.get("Comments", "")).strip()
            if additional_comments and additional_comments.lower() != "nan":
                comment_parts.append(additional_comments)

            if comment_parts:
                if not self.append_comments(comment_parts, "MNSUTB"):
                    return False

            return True
        except Exception as e:
            logging.error(f"Error handling MNSUTB fields: {e}")
            return False

    def append_comments(self, comment_parts, context_label="Document"):
        normalized_parts = []
        for part in comment_parts:
            part = self.normalize_irt_text(part).strip()
            if not part or part.lower() == "nan":
                continue
            if part not in normalized_parts:
                normalized_parts.append(part)

        if not normalized_parts:
            logging.info(f"No new comments to add for {context_label}.")
            return True

        for attempt in range(1, 4):
            try:
                self.handle_any_alert(timeout=1)
                comments_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]'))
                )
                if not comments_field.is_enabled() or comments_field.get_attribute("readonly") == "true":
                    logging.warning(
                        "%s comments field is not interactable on attempt %d/3; retrying.",
                        context_label,
                        attempt,
                    )
                    time.sleep(1)
                    continue

                existing_text = comments_field.get_attribute("value").strip()
                clean_parts = [
                    part for part in normalized_parts
                    if part not in existing_text
                ]

                if not clean_parts:
                    logging.info(f"No new comments to add for {context_label}.")
                    return True

                if existing_text:
                    if existing_text.endswith("."):
                        existing_text = existing_text[:-1].strip()
                    updated_text = f"{existing_text}; {'; '.join(clean_parts)}"
                else:
                    updated_text = "; ".join(clean_parts)

                updated_text = self.normalize_irt_text(updated_text)
                comments_field.clear()
                comments_field.send_keys(updated_text)
                logging.info(f"Updated {context_label} comments field: {updated_text}")
                return True
            except UnexpectedAlertPresentException:
                self.handle_any_alert(timeout=3)
            except Exception as e:
                if attempt < 3:
                    logging.warning(
                        "Failed to update %s comments on attempt %d/3: %s",
                        context_label,
                        attempt,
                        e,
                    )
                    time.sleep(1)
                    continue
                logging.error(f"Failed to update {context_label} comments after 3 attempts: {e}")
                return False

        return False


    def handle_unexpected_alert(self):
        """Handles unexpected alerts, especially for duplicate documents."""
        try:
            alert = WebDriverWait(self.driver, 3).until(EC.alert_is_present())
            alert_text = alert.text
            logging.warning(f"Caught unexpected alert: '{alert_text}'")
            alert.accept()
            if "duplicate document" in alert_text.lower():
                logging.info("Handling duplicate document overlay after unexpected alert.")
                self.handle_duplicate_overlay()
                return True  # Indicates a duplicate was handled
        except TimeoutException:
            return False  # No alert was present
        except Exception as e:
            logging.error(f"Error in handle_unexpected_alert")
            return False
        return False

    def is_ready_to_process_enabled(self):
        """Checks if the 'Ready to Process' checkbox is enabled and clickable."""
        try:
            checkbox = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.XPATH, '//*[@id="readyToProcess"]'))
            )
            return checkbox.is_enabled()
        except TimeoutException:
            logging.error("Could not find the 'Ready to Process' checkbox.")
            return False
        except Exception as e:
            logging.error(f"Error checking 'Ready to Process' checkbox state")
            return False

    def handle_any_alert(self, timeout=3, archive_as_duplicate=None):
        return run_handle_any_alert(
            self,
            timeout=timeout,
            archive_as_duplicate=archive_as_duplicate,
        )

    def accept_pending_alerts(self, initial_timeout=3, followup_timeout=1, max_alerts=5):
        return run_accept_pending_alerts(
            self,
            initial_timeout=initial_timeout,
            followup_timeout=followup_timeout,
            max_alerts=max_alerts,
        )

    def handle_routing_and_save(self, is_counsel, row_index, skip_route_and_ready=False):
        return run_handle_routing_and_save(
            self,
            is_counsel,
            row_index,
            skip_route_and_ready=skip_route_and_ready,
        )

    def submit_irt_form(self, file_path, row_index):
        try:
            self.safe_alert_accept()
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            logging.info("IRT Form window closed after submission.")
        except Exception as e:
            logging.error(f"Unhandled error in submit_irt_form()")

    def dispatch_document_run(
        self,
        full_df,
        filtered_counsel_df,
        filtered_main_df,
        file_path,
        update_progress,
        *,
        dar_mode=False,
        wc_mode=False,
        mspb_mode=False,
        itc_mode=False,
        irsplr_mode=False,
        ohtax0_mode=False,
        mnsutb_mode=False,
        mework_mode=False,
    ):
        mode_kwargs = dict(
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            mspb_mode=mspb_mode,
            itc_mode=itc_mode,
            irsplr_mode=irsplr_mode,
            ohtax0_mode=ohtax0_mode,
            mnsutb_mode=mnsutb_mode,
        )
        if mework_mode:
            mode_kwargs["mework_mode"] = True
        return run_dispatch_document_run(
            self,
            full_df,
            filtered_counsel_df,
            filtered_main_df,
            file_path,
            update_progress,
            **mode_kwargs,
        )

    def dispatch_shared_run(
        self,
        counsel_df,
        main_df,
        full_df,
        file_path,
        update_progress,
        *,
        dar_mode=False,
        wc_mode=False,
        mosu00_mode=False,
    ):
        return run_dispatch_shared_run(
            self,
            counsel_df,
            main_df,
            full_df,
            file_path,
            update_progress,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            **({"mosu00_mode": True} if mosu00_mode else {}),
        )

    def finalize_shared_run(self):
        return run_finalize_shared_run(self, error_log_entries)

    def process_rows(self, full_df, file_path, update_progress, dar_mode=False, wc_mode=False, mspb_mode=False, itc_mode=False, irsplr_mode=False, ohtax0_mode=False, mnsutb_mode=False, mework_mode=False, mosu00_mode=False):
        counsel_df, main_df = None, None
        try:
            self.full_df = full_df

            counsel_df, main_df = filter_mapping_data(full_df, dar_mode, wc_mode, mspb_mode=mspb_mode)

            document_mode_kwargs = dict(
                dar_mode=dar_mode,
                wc_mode=wc_mode,
                mspb_mode=mspb_mode,
                itc_mode=itc_mode,
                irsplr_mode=irsplr_mode,
                ohtax0_mode=ohtax0_mode,
                mnsutb_mode=mnsutb_mode,
            )
            if mework_mode:
                document_mode_kwargs["mework_mode"] = True
            document_run = self.dispatch_document_run(
                full_df,
                counsel_df,
                main_df,
                file_path,
                update_progress,
                **document_mode_kwargs,
            )
            if document_run is not None:
                return document_run.counsel_df, document_run.main_df

            shared_run = self.dispatch_shared_run(
                counsel_df,
                main_df,
                full_df,
                file_path,
                update_progress,
                dar_mode=dar_mode,
                wc_mode=wc_mode,
                mosu00_mode=mosu00_mode,
            )
            counsel_df = shared_run.counsel_df
            main_df = shared_run.main_df

            self.finalize_shared_run()

            # This is the correct place for the return statement for this function
            return counsel_df, main_df

        except Exception as e:
            msg = str(e)
            # List of phrases that indicate a normal, non-error outcome
            normal_outcomes = [
                "already processed",
                "No rows to process",
                "No valid data",
                "All documents processed successfully",
                "Some documents processed successfully",
                "All documents were already processed",
                "No new routing needed"
            ]
            if any(phrase in msg for phrase in normal_outcomes):
                logging.info(f"Row processing ended normally: {msg}")
            else:
                logging.error(f"Failed during row processing: {msg}", exc_info=True)
            # Ensure it returns something iterable on failure to prevent UI crash
            return pd.DataFrame(), pd.DataFrame()

    def safe_alert_accept(self):
        handled_alert, duplicate_seen = self.accept_pending_alerts(initial_timeout=5)
        if duplicate_seen:
            logging.info("Duplicate alert detected. Handling duplicate popup dialog...")
            self.handle_duplicate_overlay()
            return "This is a duplicate document"
        return "ALERT_HANDLED" if handled_alert else None

    def should_archive_duplicate(self, archive_as_duplicate=None):
        return run_should_archive_duplicate(
            self,
            archive_as_duplicate=archive_as_duplicate,
        )

    def handle_duplicate_overlay(self, archive_as_duplicate=None):
        """Handle the duplicate dialog using the current route-specific duplicate policy."""
        return run_handle_duplicate_overlay(
            self,
            archive_as_duplicate=archive_as_duplicate,
        )

    def handle_duplicate_lni_popup(self, archive_as_duplicate=None):
        return run_handle_duplicate_lni_popup(
            self,
            archive_as_duplicate=archive_as_duplicate,
        )

    def click_duplicate_process_radio(self, timeout=10):
        return run_click_duplicate_process_radio(self, timeout=timeout)

    def click_duplicate_archive_radio(self, timeout=10):
        return run_click_duplicate_archive_radio(self, timeout=timeout)

    def find_duplicate_archive_option(self, timeout=10):
        return run_find_duplicate_archive_option(self, timeout=timeout)

    def click_duplicate_continue_button(self, timeout=10):
        return run_click_duplicate_continue_button(self, timeout=timeout)

    def find_duplicate_continue_button(self, timeout=10):
        return run_find_duplicate_continue_button(self, timeout=timeout)

    def click_duplicate_dialog_element(self, element):
        return run_click_duplicate_dialog_element(self, element)

    def wait_for_duplicate_overlay_to_clear(self, timeout=15):
        return run_wait_for_duplicate_overlay_to_clear(
            self,
            timeout=timeout,
        )

    def element_is_inside_visible_dialog(self, element):
        return run_element_is_inside_visible_dialog(self, element)

    def log_duplicate_overlay_diagnostics(self):
        return run_log_duplicate_overlay_diagnostics(self)

    def prepare_common_fields(self, file_name, decision_date=None, dar_mode=False, wc_mode=False, docket_override=None, court=None):
        return run_prepare_common_fields(
            self,
            file_name,
            decision_date=decision_date,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            docket_override=docket_override,
            court=court,
            format_docket_number=CaseLawRouter.format_docket_number,
        )

    def select_dropdown_by_visible_text_or_value(self, xpath, selection, field_name):
        try:
            dropdown_element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            select = Select(dropdown_element)
            try:
                select.select_by_visible_text(selection)
            except Exception:
                select.select_by_value(selection)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('change'))", dropdown_element)
            logging.info(f"{field_name} selected: {selection}")
            self.handle_any_alert(timeout=2)
            return True
        except UnexpectedAlertPresentException:
            self.handle_any_alert(timeout=3)
            logging.info(f"{field_name} selected after alert handling: {selection}")
            return True
        except Exception as e:
            logging.error(f"Could not select {field_name}: {selection}")
            return False

    def get_selected_dropdown_text(self, dropdown_element):
        try:
            return str(self.driver.execute_script(
                """
                const select = arguments[0];
                if (!select) return '';
                const option = select.options && select.selectedIndex >= 0
                    ? select.options[select.selectedIndex]
                    : null;
                return option
                    ? (option.textContent || option.label || option.value || '').trim()
                    : (select.value || '').trim();
                """,
                dropdown_element,
            ) or "").strip()
        except Exception as e:
            logging.warning(f"Could not read selected dropdown text: {e}")
            return ""

    def set_dropdown_by_visible_text(self, dropdown_element, visible_text):
        try:
            return bool(self.driver.execute_script(
                """
                const select = arguments[0];
                const target = String(arguments[1] || '').trim().toUpperCase();
                if (!select || !select.options) return false;
                const option = Array.from(select.options).find((item) => {
                    return String(item.textContent || item.label || item.value || '').trim().toUpperCase() === target;
                });
                if (!option) return false;
                select.value = option.value;
                option.selected = true;
                select.dispatchEvent(new Event('input', { bubbles: true }));
                select.dispatchEvent(new Event('change', { bubbles: true }));
                return true;
                """,
                dropdown_element,
                visible_text,
            ))
        except Exception as e:
            logging.warning(f"Could not set dropdown to {visible_text}: {e}")
            return False

    def dropdown_text_matches(self, actual_text, expected_text):
        return str(actual_text or "").strip().upper() == str(expected_text or "").strip().upper()

    def select_source_detail(self, source_detail):
        if not source_detail or str(source_detail).strip().lower() == "nan":
            return True

        resolved_source_detail = resolve_source_detail(source_detail)
        if not resolved_source_detail:
            logging.warning(f"Invalid Source Detail input: {source_detail}")
            return False

        return self.select_dropdown_by_visible_text_or_value(
            '//*[@id="sourceDetails"]',
            resolved_source_detail,
            "Source Detail",
        )

    def handle_mspb_fields(self, row, mspb_metadata):
        try:
            case_name_xpath = '//*[@id="caseName"]'
            try:
                field = self.wait.until(EC.presence_of_element_located((By.XPATH, case_name_xpath)))
                existing_case_name = self.wait_for_existing_field_text(case_name_xpath, timeout=6)
                if existing_case_name:
                    logging.info(f"MSPB Case Name already present; leaving unchanged: {existing_case_name[:120]}")
                else:
                    if field.is_enabled() and field.get_attribute("readonly") != "true":
                        field.clear()
                        field.send_keys("RE")
                        logging.info("MSPB Case Name was blank; set to RE.")
                    else:
                        logging.info("Skipped MSPB Case Name because it is not interactable.")
            except Exception:
                logging.error("Error setting MSPB case name")

            if not self.select_source_detail(mspb_metadata.source_detail):
                return False

            comment_parts = []
            if getattr(mspb_metadata, "comments_text", ""):
                comment_parts.append(mspb_metadata.comments_text)

            additional_comments = str(row.get("Comments", "")).strip()
            if additional_comments and additional_comments.lower() != "nan":
                comment_parts.append(additional_comments)

            if comment_parts:
                self.append_comments(comment_parts, "MSPB")

            return True
        except Exception as e:
            logging.error(f"Error handling MSPB fields: {e}")
            return False

    def wait_for_existing_field_text(self, xpath, timeout=6):
        """Wait briefly for a field that IRT may populate asynchronously."""
        deadline = time.time() + timeout
        last_value = ""

        while time.time() < deadline:
            try:
                field = self.driver.find_element(By.XPATH, xpath)
                value = self.get_field_existing_text(field)
                if value:
                    return value
                last_value = value
            except Exception:
                pass
            time.sleep(0.5)

        return last_value

    def get_field_existing_text(self, field):
        try:
            value = self.driver.execute_script(
                """
                const el = arguments[0];
                return (
                    el.value ||
                    el.getAttribute('value') ||
                    el.innerText ||
                    el.textContent ||
                    ''
                ).trim();
                """,
                field,
            )
            return str(value or "").strip()
        except Exception:
            try:
                return (field.get_attribute("value") or "").strip()
            except Exception:
                return ""


    def handle_counsel_fields(self, row, dar_mode=False, wc_mode=False):
        return run_handle_counsel_fields(
            self,
            row,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            format_docket_number=CaseLawRouter.format_docket_number,
        )

    def find_main_opinion_lni_for_counsel(self, counsel_docket, counsel_row, dar_mode=False, wc_mode=False):
        """Find the Main Opinion LNI for a counsel document by matching docket numbers"""
        try:
            # Get the full dataframe from the class instance
            if hasattr(self, 'full_df') and self.full_df is not None:
                # Look for main opinion rows with matching docket
                for _, row in self.full_df.iterrows():
                    if not is_counsel(str(row.get("FileName", "")), dar_mode, wc_mode):
                        main_docket = CaseLawRouter.format_docket_number(None, row.get("FileName", ""), dar_mode, wc_mode)
                        if main_docket and main_docket == counsel_docket:
                            main_lni = str(row.get("LNI", "")).strip()
                            if main_lni and main_lni.lower() != "nan":
                                logging.info(f"Found Main Opinion LNI {main_lni} for counsel docket {counsel_docket}")
                                return main_lni
            return None
        except Exception as e:
            logging.error(f"Error finding Main Opinion LNI for counsel")
            return None

    def find_main_opinion_date_for_counsel(self, counsel_docket, counsel_file_name, dar_mode=False, wc_mode=False):
        """Find the Main Opinion decision date for a counsel document by matching docket numbers"""
        try:
            # Get the full dataframe from the class instance
            if hasattr(self, 'full_df') and self.full_df is not None:
                # Look for main opinion rows with matching docket
                for _, row in self.full_df.iterrows():
                    main_file_name = str(row.get("FileName", "")).strip()
                    if not is_counsel(main_file_name, dar_mode, wc_mode):
                        main_docket = CaseLawRouter.format_docket_number(None, main_file_name, dar_mode, wc_mode)
                        if main_docket and main_docket == counsel_docket:
                            # Extract date from main opinion filename
                            main_date = self.extract_decision_date_from_filename(main_file_name)
                            if main_date:
                                logging.info(f"Found Main Opinion date {main_date} for counsel docket {counsel_docket}")
                                return main_date
            return None
        except Exception as e:
            logging.error(f"Error finding Main Opinion date for counsel")
            return None

    def handle_main_opinion_fields(self, row, full_df, row_index, file_path, dar_mode=False, wc_mode=False):
        return run_handle_main_opinion_fields(
            self,
            row,
            full_df,
            row_index,
            file_path,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            format_docket_number=CaseLawRouter.format_docket_number,
        )

    def handle_related_ln_is(self, row, full_df, row_index=None, file_path=None, dar_mode=False, wc_mode=False):
        return run_handle_related_ln_is(
            self,
            row,
            full_df,
            row_index=row_index,
            file_path=file_path,
            dar_mode=dar_mode,
            wc_mode=wc_mode,
            format_docket_number=CaseLawRouter.format_docket_number,
        )

    def extract_decision_date_from_filename(self, file_name):
        """
        Extract decision date from filename, supporting both MMDDYYYY and YYYYMMDD formats.
        
        Args:
            file_name (str): Filename to extract date from
            
        Returns:
            str: Date in MM-DD-YYYY format if found, None otherwise
        """
        try:
            # Look for 8-digit date pattern in filename
            match = re.search(r'[_-](\d{8})(?=[_-]|\.|$)|^(\d{8})[_-]|[_-](\d{8})$', str(file_name))
            if match:
                # Get the first non-None group
                date_digits = None
                for i in range(1, 4):
                    if match.group(i):
                        date_digits = match.group(i)
                        break
                
                if date_digits and len(date_digits) == 8:
                    # Try YYYYMMDD format first (year 1900-2099, month 01-12, day 01-31)
                    year = int(date_digits[:4])
                    month = int(date_digits[4:6])
                    day = int(date_digits[6:8])
                    
                    if 1900 <= year <= 2099 and 1 <= month <= 12 and 1 <= day <= 31:
                        # Format as MM-DD-YYYY
                        return f"{month:02d}-{day:02d}-{year}"
                    
                    # Try MMDDYYYY format as fallback (month 01-12, day 01-31, year 1900-2099)
                    month = int(date_digits[:2])
                    day = int(date_digits[2:4])
                    year = int(date_digits[4:])
                    
                    if 1 <= month <= 12 and 1 <= day <= 31 and 1900 <= year <= 2099:
                        # Format as MM-DD-YYYY
                        return f"{month:02d}-{day:02d}-{year}"
        except Exception as e:
            logging.error(f"Error extracting decision date from filename '{file_name}': {e}")
        # If not found or invalid, return None to trigger fallback
        return None

    def process_main_opinion_with_attachments(self, main_file, attachment_files, dar_mode=True):
        """
        Process a main opinion document with its attached counsel and ARC files.
        
        Args:
            main_file (str): Main opinion filename
            attachment_files (list): List of counsel and ARC filenames to attach
            dar_mode (bool): Whether to use DAR mode processing
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"Processing main opinion {main_file} with {len(attachment_files)} attachments")
            
            # Create a mock row for the main opinion file
            mock_row = {
                'FileName': main_file,
                'LNI': '',  # Will be filled during processing
                'Comments': '',
                'RecycledCounselLNI': ''
            }
            
            # Process the main opinion
            # This would integrate with the existing main opinion processing logic
            # For now, we'll use the existing handle_main_opinion_fields method
            success = self.handle_main_opinion_fields(
                mock_row, 
                self.full_df if hasattr(self, 'full_df') else None,
                row_index=None,
                file_path=None,
                dar_mode=dar_mode,
                wc_mode=False
            )
            
            if success:
                logging.info(f"Successfully processed main opinion {main_file}")
                # Here you would add logic to attach the counsel and ARC files
                # This would involve updating the related LNI fields
                for attachment in attachment_files:
                    logging.info(f"Attached {attachment} to main opinion {main_file}")
            
            return success
            
        except Exception as e:
            logging.error(f"Error processing main opinion {main_file}: {str(e)}")
            return False

    def process_standalone_counsel(self, counsel_file, dar_mode=True):
        """
        Process a standalone counsel or ARC file.
        
        Args:
            counsel_file (str): Counsel or ARC filename
            dar_mode (bool): Whether to use DAR mode processing
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"Processing standalone counsel/ARC file: {counsel_file}")
            
            # Create a mock row for the counsel file
            mock_row = {
                'FileName': counsel_file,
                'LNI': '',  # Will be filled during processing
                'Comments': '',
                'RecycledCounselLNI': ''
            }
            
            # Process the counsel file
            # This would integrate with the existing counsel processing logic
            # For now, we'll use the existing handle_counsel_fields method
            success = self.handle_counsel_fields(
                mock_row,
                dar_mode=dar_mode,
                wc_mode=False
            )
            
            if success:
                file_type = "ARC document" if 'arc' in counsel_file.lower() else "counsel file"
                logging.info(f"Successfully processed standalone {file_type}: {counsel_file}")
            
            return success
            
        except Exception as e:
            logging.error(f"Error processing standalone counsel file {counsel_file}: {str(e)}")
            return False

