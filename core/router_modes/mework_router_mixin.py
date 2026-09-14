"""MEWORK PDF metadata acquisition isolated from the shared router."""

from dataclasses import replace
import logging
import threading
import time
from urllib.parse import urljoin

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

from ..mework_extractor import (
    MEWORKMetadata,
    parse_mework_document_text,
    parse_mework_pdf_bytes,
)
from ..smducar_config import (
    mework_content_fingerprint_buffer,
    mspb_metadata_buffer,
)


_mework_duplicate_lock = threading.Lock()


class MEWORKRouterMixin:
    """Own MEWORK metadata capture, duplicate policy, and PDF retrieval."""

    def record_mework_metadata(
        self,
        row_index,
        row,
        lni,
        metadata=None,
        metadata_status="Attempted",
    ):
        self.record_mspb_metadata(
            row_index,
            row,
            lni,
            metadata=metadata,
            metadata_status=metadata_status,
        )
        if row_index not in mspb_metadata_buffer:
            return
        record = mspb_metadata_buffer[row_index]
        record["Metadata Type"] = "MEWORK"
        if metadata and (
            getattr(metadata, "is_true_duplicate", False)
            or getattr(metadata, "is_excluded", False)
        ):
            record["Route"] = "Archive"
        duplicate_lni = getattr(metadata, "duplicate_of_lni", "") if metadata else ""
        if duplicate_lni and not getattr(metadata, "is_excluded", False):
            prepared = record.get("Prepared Comments", "") or ""
            duplicate_comment = f"Dup of {duplicate_lni}"
            if duplicate_comment not in prepared:
                record["Prepared Comments"] = (
                    f"{prepared}; {duplicate_comment}"
                    if prepared
                    else duplicate_comment
                )

    def mark_mework_duplicate_status(
        self,
        row_index,
        row,
        lni,
        metadata: MEWORKMetadata,
    ):
        if not metadata or not getattr(metadata, "content_fingerprint", ""):
            return metadata
        if getattr(metadata, "is_excluded", False):
            logging.info(
                "MEWORK document is excluded; exclusion takes priority over "
                "duplicate classification."
            )
            return metadata

        current_label = (
            str(row.get("FileName", "")).strip() or str(lni or "").strip()
        )
        current_lni = str(lni or "").strip()
        with _mework_duplicate_lock:
            existing = mework_content_fingerprint_buffer.get(
                metadata.content_fingerprint
            )
            if existing:
                existing_label = (
                    existing.get("label", "")
                    if isinstance(existing, dict)
                    else str(existing)
                )
                existing_lni = (
                    existing.get("lni", "") if isinstance(existing, dict) else ""
                )
                logging.warning(
                    "Confirmed MEWORK true duplicate by normalized PDF text "
                    "fingerprint: %s duplicates %s",
                    current_label,
                    existing_label,
                )
                return replace(
                    metadata,
                    is_true_duplicate=True,
                    duplicate_of=existing_label,
                    duplicate_of_lni=existing_lni,
                )
            mework_content_fingerprint_buffer[metadata.content_fingerprint] = {
                "label": current_label,
                "lni": current_lni,
            }
        return metadata

    def extract_mework_metadata_from_search_result(self, row, row_index=None):
        try:
            link_element = self.find_mspb_file_name_link(row)
            if link_element is None:
                logging.warning(
                    "MEWORK File Name link was not found in the search results."
                )
                return None
            metadata = self.open_mework_link_and_extract_metadata(link_element, row)
            if metadata and getattr(metadata, "has_text_content", False):
                return metadata
            logging.warning("MEWORK PDF did not expose readable text.")
            return None
        except Exception as exc:
            logging.error("Error extracting MEWORK metadata from PDF: %s", exc)
            return None

    def open_mework_link_and_extract_metadata(self, element, row):
        main_tab = self.driver.current_window_handle
        before_handles = set(self.driver.window_handles)
        before_downloads = self.snapshot_mework_downloads()
        opened_tab = None
        file_name = str(row.get("FileName", "")).strip()
        try:
            href = self._get_element_href(element)
            expected_filename = self.get_filename_from_document_href(href) or file_name
            self.enable_chrome_downloads(self.mework_download_dir)
            self.enable_browser_network_capture()
            if href:
                target_url = urljoin(self.driver.current_url, href)
                self.driver.execute_script(
                    "window.open(arguments[0], '_blank');",
                    target_url,
                )
            else:
                target_url = None
                element.click()

            metadata = self.wait_for_mework_downloaded_metadata(
                before_downloads,
                expected_filename,
                timeout=20,
            )
            if metadata:
                return metadata
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: len(driver.window_handles) > len(before_handles)
                )
                new_handles = set(self.driver.window_handles) - before_handles
                if new_handles:
                    opened_tab = new_handles.pop()
                    self.driver.switch_to.window(opened_tab)
            except TimeoutException:
                logging.info(
                    "MEWORK link did not open a readable tab yet; continuing "
                    "to watch for download."
                )
            metadata = self.wait_for_mework_downloaded_metadata(
                before_downloads,
                expected_filename,
                timeout=25,
            )
            if metadata:
                return metadata
            logging.info("Opened MEWORK PDF link in a browser tab.")
            metadata = self.wait_for_mework_metadata_from_open_tab(
                target_url,
                before_downloads=before_downloads,
                expected_filename=expected_filename,
                timeout=45,
            )
            if metadata:
                return metadata
            logging.warning("MEWORK PDF tab opened, but metadata could not be extracted.")
            return None
        except Exception as exc:
            logging.warning("Could not read MEWORK document in browser tab: %s", exc)
            return None
        finally:
            try:
                if opened_tab and opened_tab in self.driver.window_handles:
                    self.driver.close()
                if main_tab in self.driver.window_handles:
                    self.driver.switch_to.window(main_tab)
            except Exception:
                pass

    def wait_for_mework_metadata_from_open_tab(
        self,
        target_url=None,
        before_downloads=None,
        expected_filename=None,
        timeout=45,
    ):
        deadline = time.time() + timeout
        self._mspb_pdf_request_ids = set()
        self._mspb_pdf_checked_request_ids = set()
        last_status_log = 0
        while time.time() < deadline:
            self.wait_for_open_tab_load_state(timeout=5)
            metadata = self.wait_for_mework_downloaded_metadata(
                before_downloads or {},
                expected_filename,
                timeout=1,
            )
            if metadata:
                return metadata
            pdf_bytes = self.get_opened_pdf_bytes_from_browser_network(
                target_url,
                timeout=1,
            )
            if pdf_bytes:
                metadata = parse_mework_pdf_bytes(
                    pdf_bytes,
                    filename_hint=expected_filename,
                )
                if metadata and metadata.has_text_content:
                    self.log_mework_metadata(metadata, "browser PDF tab")
                    return metadata
            for source, browser_text in (
                ("Chrome accessibility tree", self.read_open_pdf_accessibility_text()),
                ("browser PDF viewer clipboard", self.copy_open_pdf_tab_text()),
                ("browser visible text", self.read_open_pdf_tab_text()),
            ):
                if self.looks_like_mework_text(browser_text):
                    metadata = parse_mework_document_text(
                        browser_text,
                        filename_hint=expected_filename,
                    )
                    if metadata and metadata.has_text_content:
                        self.log_mework_metadata(metadata, source)
                        return metadata
            if time.time() - last_status_log >= 10:
                logging.info(
                    "Waiting for MEWORK PDF tab to finish loading/expose text..."
                )
                last_status_log = time.time()
            time.sleep(2)
        self.log_mspb_pdf_tab_diagnostics("MEWORK")
        return None

    def snapshot_mework_downloads(self):
        self.mework_download_dir.mkdir(parents=True, exist_ok=True)
        snapshot = {}
        for path in self.mework_download_dir.glob("*"):
            if path.is_file():
                try:
                    stat = path.stat()
                    snapshot[path.name.lower()] = (stat.st_mtime, stat.st_size)
                except Exception:
                    continue
        return snapshot

    def wait_for_mework_downloaded_metadata(
        self,
        before_downloads,
        expected_filename=None,
        timeout=30,
    ):
        deadline = time.time() + timeout
        while time.time() < deadline:
            pdf_path = self.find_completed_mework_download(
                before_downloads,
                expected_filename,
            )
            if pdf_path:
                try:
                    metadata = parse_mework_pdf_bytes(
                        pdf_path.read_bytes(),
                        filename_hint=pdf_path.name,
                    )
                    if metadata and metadata.has_text_content:
                        self.log_mework_metadata(
                            metadata,
                            f"downloaded PDF {pdf_path.name}",
                        )
                        return metadata
                    logging.warning(
                        "Downloaded MEWORK PDF %s did not expose readable text.",
                        pdf_path.name,
                    )
                    return None
                except Exception as exc:
                    logging.warning(
                        "Downloaded MEWORK PDF could not be parsed: %s (%s)",
                        pdf_path,
                        exc,
                    )
            time.sleep(0.5)
        return None

    def find_completed_mework_download(
        self,
        before_downloads,
        expected_filename=None,
    ):
        expected_lower = expected_filename.lower() if expected_filename else None
        active_downloads = list(self.mework_download_dir.glob("*.crdownload"))
        candidates = []
        for path in self.mework_download_dir.glob("*.pdf"):
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
                if not any(
                    str(download).lower().startswith(str(path).lower())
                    for download in active_downloads
                ):
                    candidates.append(path)
        if not candidates:
            return None
        candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return candidates[0]

    @staticmethod
    def looks_like_mework_text(text):
        if not text:
            return False
        text_upper = text.upper()
        return (
            "WORKERS' COMPENSATION BOARD" in text_upper
            or "WCB#" in text_upper
            or "WCB NO" in text_upper
        )

    @staticmethod
    def log_mework_metadata(metadata, source):
        logging.info(
            "Extracted MEWORK metadata from %s: court=%s docket=%s "
            "decision_date=%s source_detail=%s other_numbers=%s excluded=%s",
            source,
            metadata.court,
            metadata.docket_number,
            metadata.decision_date,
            metadata.source_detail,
            "; ".join(metadata.other_numbers or ()),
            getattr(metadata, "is_excluded", False),
        )
