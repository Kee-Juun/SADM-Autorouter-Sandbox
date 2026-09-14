"""MOSU00 browser-routing mixin adapted from the production router.

The hybrid MOSU mode keeps its specialized HTML/table Selenium behavior isolated
from the shared SMD/DAR flow.
"""

import logging
import time
from urllib.parse import urljoin

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from ..mosu00_extractor import (
    MOSU00Metadata,
    find_mosu00_source_file,
    parse_mosu00_html_file,
    parse_mosu00_html_text,
)
from ..smducar_config import mspb_metadata_buffer, status_updates_buffer


class MOSU00RouterMixin:
    """Specialized metadata acquisition and table-case form behavior."""

    def record_mosu00_metadata(self, row_index, row, lni, metadata=None, metadata_status="Attempted"):
            """Capture MOSU00 table metadata used for the final workbook sheet."""
            self.record_mspb_metadata(row_index, row, lni, metadata=metadata, metadata_status=metadata_status)
            if row_index in mspb_metadata_buffer:
                mspb_metadata_buffer[row_index]["Metadata Type"] = "MOSU00"
                if metadata:
                    child_dockets = getattr(metadata, "child_dockets", ()) or ()
                    mspb_metadata_buffer[row_index]["Extracted Other Numbers"] = "; ".join(child_dockets[1:])
                    mspb_metadata_buffer[row_index]["Prepared Comments"] = getattr(metadata, "comments_text", "") or ""
    
    def extract_mosu00_metadata_from_search_result(self, row, row_index=None, file_path=None):
            """Open the result HTML from the File Name column and parse MOSU00 table metadata."""
            try:
                link_element = self.find_mspb_file_name_link(row)
                if link_element is not None:
                    metadata = self.open_mosu00_link_and_extract_metadata(link_element, row)
                    if metadata:
                        return metadata
                    logging.warning("MOSU00 table HTML link opened, but metadata was not readable.")
                else:
                    logging.warning("MOSU00 File Name link was not found in the search results.")
    
                file_name = str(row.get("FileName", "")).strip()
                local_file = find_mosu00_source_file(file_name, reference_path=file_path)
                if local_file:
                    metadata = parse_mosu00_html_file(local_file)
                    if metadata:
                        self.log_mosu00_metadata(metadata, f"local file {local_file.name}")
                        return metadata
                    logging.warning("MOSU00 local HTML fallback could not parse required metadata: %s", local_file)
    
                return None
            except Exception as e:
                logging.error(f"Error extracting MOSU00 table metadata from HTML: {e}")
                return None
    
    def open_mosu00_link_and_extract_metadata(self, element, row):
            """Open the linked MOSU00 HTML document in a browser tab and parse table metadata."""
            main_tab = self.driver.current_window_handle
            main_url = ""
            try:
                main_url = self.driver.current_url
            except Exception:
                pass
            before_handles = set(self.driver.window_handles)
            before_downloads = self.snapshot_mosu00_downloads()
            opened_tab = None
            file_name = str(row.get("FileName", "")).strip()
    
            try:
                href = self._get_element_href(element)
                expected_filename = self.get_filename_from_document_href(href) or file_name
                self.enable_chrome_downloads(self.mosu00_download_dir)
                if href:
                    target_url = urljoin(self.driver.current_url, href)
                    self.driver.execute_script("window.open(arguments[0], '_blank');", target_url)
                else:
                    target_url = None
                    element.click()
    
                downloaded_metadata = self.wait_for_mosu00_downloaded_metadata(
                    before_downloads,
                    expected_filename,
                    timeout=8,
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
                    logging.info("MOSU00 table link did not open a new tab; trying to read the current browser context.")
    
                downloaded_metadata = self.wait_for_mosu00_downloaded_metadata(
                    before_downloads,
                    expected_filename,
                    timeout=12,
                )
                if downloaded_metadata:
                    return downloaded_metadata
    
                metadata = self.wait_for_mosu00_metadata_from_open_tab(
                    target_url,
                    expected_filename=expected_filename,
                    timeout=30,
                )
                if metadata:
                    return metadata
    
                logging.warning("MOSU00 HTML tab opened, but metadata could not be extracted from the browser-rendered document.")
                return None
            except Exception as e:
                logging.warning(f"Could not read MOSU00 table document in browser tab: {e}")
                return None
            finally:
                try:
                    if opened_tab and opened_tab in self.driver.window_handles:
                        self.driver.close()
                    if main_tab in self.driver.window_handles:
                        self.driver.switch_to.window(main_tab)
                        if not opened_tab and main_url:
                            try:
                                current_url = self.driver.current_url
                                if current_url != main_url:
                                    self.driver.back()
                                    self.wait_for_open_tab_load_state(timeout=10)
                                    logging.info("Returned to Search Inventory after reading MOSU00 HTML in the same tab.")
                            except Exception as exc:
                                logging.warning("Could not return to Search Inventory after MOSU00 HTML read: %s", exc)
                except Exception:
                    pass
    
    def wait_for_mosu00_metadata_from_open_tab(self, target_url=None, expected_filename=None, timeout=30):
            deadline = time.time() + timeout
            last_status_log = 0
    
            while time.time() < deadline:
                self.wait_for_open_tab_load_state(timeout=5)
    
                visible_text = self.read_open_pdf_tab_text()
                metadata = parse_mosu00_html_text(visible_text, filename_hint=expected_filename)
                if metadata:
                    self.log_mosu00_metadata(metadata, "browser visible HTML")
                    return metadata
    
                page_source = ""
                try:
                    page_source = self.driver.page_source or ""
                except Exception:
                    page_source = ""
                metadata = parse_mosu00_html_text(page_source, filename_hint=expected_filename)
                if metadata:
                    self.log_mosu00_metadata(metadata, "browser page source")
                    return metadata
    
                if time.time() - last_status_log >= 10:
                    logging.info("Waiting for MOSU00 HTML document to finish loading/expose table text...")
                    last_status_log = time.time()
    
                time.sleep(1.5)
    
            self.log_mspb_pdf_tab_diagnostics("MOSU00")
            return None
    
    def snapshot_mosu00_downloads(self):
            self.mosu00_download_dir.mkdir(parents=True, exist_ok=True)
            snapshot = {}
            for path in self.mosu00_download_dir.glob("*"):
                if path.is_file():
                    try:
                        stat = path.stat()
                        snapshot[path.name.lower()] = (stat.st_mtime, stat.st_size)
                    except Exception:
                        continue
            return snapshot
    
    def wait_for_mosu00_downloaded_metadata(self, before_downloads, expected_filename=None, timeout=20):
            deadline = time.time() + timeout
            while time.time() < deadline:
                html_path = self.find_completed_mosu00_download(before_downloads, expected_filename)
                if html_path:
                    try:
                        metadata = parse_mosu00_html_file(html_path)
                        if metadata:
                            self.log_mosu00_metadata(metadata, f"downloaded HTML {html_path.name}")
                            return metadata
                        logging.warning("Downloaded MOSU00 HTML %s did not contain required table metadata.", html_path.name)
                        return None
                    except Exception as e:
                        logging.warning(f"Downloaded MOSU00 HTML could not be parsed: {html_path} ({e})")
                time.sleep(0.5)
            return None
    
    def find_completed_mosu00_download(self, before_downloads, expected_filename=None):
            expected_lower = expected_filename.lower() if expected_filename else None
            active_downloads = list(self.mosu00_download_dir.glob("*.crdownload"))
            candidates = []
    
            for path in list(self.mosu00_download_dir.glob("*.htm")) + list(self.mosu00_download_dir.glob("*.html")):
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
    
    def log_mosu00_metadata(self, metadata, source):
            logging.info(
                "Extracted MOSU00 table metadata from %s: court=%s parent_docket=%s decision_date=%s source_detail=%s child_dockets=%s",
                source,
                metadata.court,
                metadata.docket_number,
                metadata.decision_date,
                metadata.source_detail,
                "; ".join(metadata.child_dockets or ()),
            )
    
    def is_route_locked_already_processed(self, context_label="Document"):
            """Return True only for the high-confidence route-locked already-processed state."""
            try:
                comments_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]')))
                route_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="route"]')))
                if not route_field.is_enabled() and comments_field.is_enabled():
                    logging.info("%s route dropdown is disabled; treating document as ALREADY PROCESSED.", context_label)
                    return True
            except Exception as e:
                logging.debug("Could not inspect route-locked already-processed state for %s: %s", context_label, e)
            return False
    
    def fill_mosu00_table_irt_form(self, row, row_index, mosu00_metadata: MOSU00Metadata):
            """Fill an IRT form for MOSU00 table-case routing."""
            try:
                if not mosu00_metadata:
                    logging.warning("Skipping MOSU00 table row because extracted metadata is missing.")
                    if row_index is not None:
                        status_updates_buffer[row_index] = "SKIPPED: MOSU00 HTML DATA NOT FOUND"
                    return "SKIPPED: MOSU00 HTML DATA NOT FOUND"
    
                file_name = str(row.get("FileName", "")).strip()
                self.prepare_common_fields(
                    file_name,
                    decision_date=mosu00_metadata.decision_date,
                    dar_mode=False,
                    wc_mode=False,
                    docket_override=mosu00_metadata.docket_number,
                    court=None,
                )
                self.handle_any_alert()
    
                if not self.handle_mosu00_table_fields(row, mosu00_metadata):
                    if self.is_route_locked_already_processed("MOSU00"):
                        status_updates_buffer[row_index] = "ALREADY PROCESSED"
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return "ALREADY PROCESSED"
                    if row_index is not None:
                        status_updates_buffer[row_index] = "SKIPPED: MOSU00 TABLE FORM FILL ERROR"
                    return "SKIPPED: MOSU00 TABLE FORM FILL ERROR"
    
                try:
                    comments_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="comments"]')))
                    route_field = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="route"]')))
    
                    if not route_field.is_enabled() and comments_field.is_enabled():
                        logging.info("Route dropdown is disabled - MOSU00 table document already processed.")
                        status_updates_buffer[row_index] = "ALREADY PROCESSED"
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return "ALREADY PROCESSED"
    
                    if not comments_field.is_enabled() and not route_field.is_enabled():
                        logging.error("MOSU00 table IRT form is non-interactable.")
                        status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return "NON-INTERACTABLE IRT FORM"
                except Exception:
                    logging.error("Could not verify MOSU00 table form interactability.")
                    status_updates_buffer[row_index] = "NON-INTERACTABLE IRT FORM"
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return "NON-INTERACTABLE IRT FORM"
    
                try:
                    route_element = self.wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="route"]')))
                    if route_element.is_enabled():
                        route_element = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="route"]')))
                        route_element.click()
                        self.handle_any_alert()
                        dropdown = Select(route_element)
                        dropdown.select_by_visible_text("Outside Conversion")
                        self.handle_any_alert()
                        logging.info("Selected MOSU00 table route: Outside Conversion")
                        self.driver.execute_script("document.getElementById('route').dispatchEvent(new Event('change'))")
                        self.handle_any_alert()
                    else:
                        raise Exception("MOSU00 table route dropdown is disabled before route selection")
                except Exception as e:
                    logging.error(f"Failed to select MOSU00 route before Ready to Process: {e}")
                    status_updates_buffer[row_index] = "ROUTE ERROR"
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return "ROUTE ERROR"
    
                overlay_appeared = self.click_ready_checkbox_and_check_overlay(False)
                self.handle_any_alert()
                if overlay_appeared == "ROUTE_ERROR":
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return "ROUTE ERROR"
                if overlay_appeared == "ALERT_HANDLED":
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return "ALERT_HANDLED"
                if overlay_appeared == "READY_NOT_CLICKABLE":
                    logging.info("Ready to Process checkbox was not clickable for MOSU00; marking document as ALREADY PROCESSED.")
                    status_updates_buffer[row_index] = "ALREADY PROCESSED"
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return "ALREADY PROCESSED"
    
                return self.handle_routing_and_save(False, row_index, skip_route_and_ready=True)
            except Exception as e:
                logging.error(f"Error in fill_mosu00_table_irt_form(): {e}")
                if row_index is not None:
                    status_updates_buffer[row_index] = "ERROR"
                return "ERROR"
    
    def handle_mosu00_table_fields(self, row, mosu00_metadata: MOSU00Metadata):
            try:
                case_name_xpath = '//*[@id="caseName"]'
                try:
                    field = self.wait.until(EC.presence_of_element_located((By.XPATH, case_name_xpath)))
                    existing_case_name = self.wait_for_existing_field_text(case_name_xpath, timeout=6)
                    if existing_case_name:
                        logging.info(f"MOSU00 Case Name already present; leaving unchanged: {existing_case_name[:120]}")
                    else:
                        if field.is_enabled() and field.get_attribute("readonly") != "true":
                            field.clear()
                            field.send_keys("RE")
                            logging.info("MOSU00 Case Name was blank; set to RE.")
                        else:
                            logging.info("Skipped MOSU00 Case Name because it is not interactable.")
                except Exception:
                    logging.error("Error setting MOSU00 case name")
    
                if not self.select_source_detail(mosu00_metadata.source_detail):
                    return False
    
                comment_parts = []
                if mosu00_metadata.comments_text:
                    comment_parts.append(mosu00_metadata.comments_text)
    
                additional_comments = str(row.get("Comments", "")).strip()
                if additional_comments and additional_comments.lower() != "nan":
                    comment_parts.append(additional_comments)
    
                if comment_parts and not self.append_comments(comment_parts, "MOSU00"):
                    return False
    
                return self.configure_mosu00_table_case(mosu00_metadata)
            except Exception as e:
                logging.error(f"Error handling MOSU00 table fields: {e}")
                return False
    
    def configure_mosu00_table_case(self, mosu00_metadata: MOSU00Metadata):
            child_dockets = [str(docket).strip() for docket in (mosu00_metadata.child_dockets or ()) if str(docket).strip()]
            if not child_dockets:
                logging.error("MOSU00 table metadata does not contain child docket numbers.")
                return False
    
            try:
                table_checkbox = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//*[@id="tableCases"]'))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", table_checkbox)
                if not table_checkbox.is_selected():
                    try:
                        table_checkbox.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", table_checkbox)
                    logging.info("Enabled MOSU00 Table Case checkbox.")
                else:
                    logging.info("MOSU00 Table Case checkbox was already enabled.")
    
                if not self.click_mosu00_table_create_button():
                    return False
                logging.info("Opened MOSU00 Table Case Entry form.")
    
                self.wait_for_mosu00_table_case_form()
    
                if not self.clear_and_fill_input('//*[@id="tableCaseNums"]', str(len(child_dockets))):
                    logging.error("Could not fill MOSU00 child LNI count.")
                    return False
    
                if not self.click_mosu00_table_submit_button():
                    return False
                logging.info("Submitted MOSU00 child LNI count: %d", len(child_dockets))
                self.wait_for_mosu00_table_case_spinner(timeout=20)
    
                for index, docket in enumerate(child_dockets):
                    field_xpath = f'//*[@id="tcDocketNum{index}"]'
                    field = WebDriverWait(self.driver, 30).until(
                        EC.presence_of_element_located((By.XPATH, field_xpath))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", field)
                    WebDriverWait(self.driver, 10).until(lambda d, item=field: item.is_enabled() and item.get_attribute("readonly") != "true")
                    field.clear()
                    field.send_keys(docket)
                    logging.info("Filled MOSU00 child docket %d/%d: %s", index + 1, len(child_dockets), docket)
                    field.send_keys(Keys.TAB)
                    self.wait_for_mosu00_table_case_spinner(timeout=20)
    
                if not self.click_mosu00_table_case_save_button():
                    return False
    
                self.accept_mosu00_table_case_save_confirmation(expected_count=len(child_dockets))
                self.wait_for_mosu00_table_case_spinner(timeout=25)
                logging.info("MOSU00 table child docket form saved successfully.")
                return True
            except Exception as e:
                logging.error(f"Error configuring MOSU00 table child LNIs: {e}")
                return False
    
    def click_mosu00_table_create_button(self):
            return self.click_mosu00_table_dialog_button(
                '//*[@id="Create"]',
                "Create/Edit",
                "MOSU00 Table Case Entry Create/Edit",
            )
    
    def click_mosu00_table_submit_button(self):
            return self.click_mosu00_table_dialog_button(
                '//*[@id="addTableCaseNumber"]',
                "Submit",
                "MOSU00 child LNI count Submit",
            )
    
    def click_mosu00_table_dialog_button(self, xpath, button_name, log_label):
            """Click MOSU00 table-case buttons even when the IRT fieldset intercepts native clicks."""
            try:
                button = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, xpath))
                )
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", button)
                self.wait_for_mosu00_table_case_spinner(timeout=8)
    
                if not button.is_enabled():
                    logging.error("%s button is present but disabled.", log_label)
                    return False
    
                click_attempts = (
                    ("native", lambda item: item.click()),
                    ("action", lambda item: ActionChains(self.driver).move_to_element(item).pause(0.2).click().perform()),
                    ("javascript", lambda item: self.driver.execute_script("arguments[0].click();", item)),
                )
                for method_name, click_method in click_attempts:
                    try:
                        click_method(button)
                        logging.info("Clicked %s button using %s click.", log_label, method_name)
                        return True
                    except Exception as exc:
                        logging.info("%s %s click failed: %s", log_label, method_name, exc)
    
                logging.error("Could not click %s button after native/action/javascript attempts.", log_label)
                return False
            except Exception as e:
                logging.error("Could not locate MOSU00 table %s button: %s", button_name, e)
                return False
    
    def wait_for_mosu00_table_case_form(self):
            header_xpath = "//*[contains(normalize-space(.), 'Choose Number of Child LNIs')]"
            WebDriverWait(self.driver, 20).until(EC.presence_of_element_located((By.XPATH, header_xpath)))
            logging.info("MOSU00 Table Case Entry form is visible.")
    
    def wait_for_mosu00_table_case_spinner(self, timeout=15):
            try:
                WebDriverWait(self.driver, timeout).until(
                    lambda d: d.execute_script(
                        """
                        const selectors = [
                            '.blockUI', '.ui-progressbar',
                            '.throbber', '.spinner', '.loading', '.ajax-loader',
                            '#throbber', '#loading'
                        ];
                        const visible = selectors.some((selector) => {
                            return Array.from(document.querySelectorAll(selector)).some((el) => {
                                const style = window.getComputedStyle(el);
                                const rect = el.getBoundingClientRect();
                                return style.display !== 'none'
                                    && style.visibility !== 'hidden'
                                    && style.opacity !== '0'
                                    && rect.width > 0
                                    && rect.height > 0;
                            });
                        });
                        const jqueryBusy = window.jQuery ? window.jQuery.active > 0 : false;
                        return !visible && !jqueryBusy;
                        """
                    )
                )
                time.sleep(0.4)
                return True
            except Exception:
                logging.info("MOSU00 table form spinner/loading wait timed out; proceeding with field checks.")
                return False
    
    def click_mosu00_table_case_save_button(self):
            self.clear_mosu00_duplicate_dialog_before_table_save()
            self.wait_for_mosu00_table_case_spinner(timeout=8)
            if self.click_mosu00_table_save_with_dom_fallback():
                return True
    
            uppercase = "'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
            save_xpaths = [
                (
                    "//div[contains(@class, 'ui-dialog') and .//*[contains(normalize-space(.), 'Choose Number of Child LNIs')]]"
                    f"//button[.//span[translate(normalize-space(.), {uppercase})='SAVE'] or translate(normalize-space(.), {uppercase})='SAVE']"
                ),
                f"//span[contains(@class, 'ui-button-text') and translate(normalize-space(.), {uppercase})='SAVE']/ancestor::button[1]",
                f"//span[contains(@class, 'ui-button-text') and translate(normalize-space(.), {uppercase})='SAVE']",
                f"//button[.//span[translate(normalize-space(.), {uppercase})='SAVE'] or translate(normalize-space(.), {uppercase})='SAVE']",
                "/html/body/div[16]/div[11]/div/button[1]",
                "/html/body/div[16]/div[11]/div/button[1]/span",
                "/html/body/div[17]/div[11]/div/button[1]",
                "/html/body/div[17]/div[11]/div/button[1]/span",
            ]
    
            for xpath in save_xpaths:
                try:
                    button = WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    button.click()
                    logging.info("Clicked MOSU00 Table Case Entry Save button.")
                    return True
                except Exception:
                    continue
    
            self.log_mosu00_table_dialog_diagnostics()
            logging.error("Could not click MOSU00 Table Case Entry Save button.")
            return False
    
    def clear_mosu00_duplicate_dialog_before_table_save(self):
            """Clear duplicate dialogs that can appear after MOSU00 child docket entry."""
            try:
                duplicate_visible = self.driver.execute_script(
                    """
                    const isVisible = (el) => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && style.opacity !== '0'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    const dialogs = Array.from(document.querySelectorAll('.ui-dialog, [role="dialog"]')).filter(isVisible);
                    return dialogs.some((dialog) => /duplicate/i.test(dialog.innerText || dialog.textContent || ''))
                        || Array.from(document.querySelectorAll('#processDuplicate')).some((el) => {
                            const dialog = el.closest ? el.closest('.ui-dialog') : null;
                            return dialog && isVisible(dialog);
                        });
                    """
                )
                if duplicate_visible:
                    logging.info("MOSU00 table Save is blocked by a duplicate dialog; processing it as New before saving child LNIs.")
                    self.handle_duplicate_overlay(archive_as_duplicate=False)
            except Exception as e:
                logging.info("MOSU00 duplicate-dialog pre-save check failed; continuing to Save attempts: %s", e)
    
    def click_mosu00_table_save_with_dom_fallback(self):
            """Find and click the Save button in the active MOSU00 table dialog by DOM context."""
            try:
                result = self.driver.execute_script(
                    """
                    const isVisible = (el) => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && style.opacity !== '0'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    const labelFor = (el) => {
                        return (el.innerText || el.textContent || el.value || el.getAttribute('aria-label') || '').trim();
                    };
                    const dialogs = Array.from(document.querySelectorAll('.ui-dialog, [role="dialog"]')).filter(isVisible);
                    const dialog = dialogs.find((item) => {
                        const text = (item.innerText || item.textContent || '').toLowerCase();
                        return text.includes('choose number of child lnis')
                            || item.querySelector('#tableCaseNums')
                            || item.querySelector('[id^="tcDocketNum"]');
                    }) || dialogs[dialogs.length - 1] || document;
    
                    const candidates = Array.from(dialog.querySelectorAll(
                        'button, input[type="button"], input[type="submit"], a, span.ui-button-text'
                    )).filter(isVisible);
    
                    const saveTextCandidate = candidates.find((item) => /\\bsave\\b/i.test(labelFor(item)));
                    let target = saveTextCandidate || null;
                    if (target && target.tagName && target.tagName.toLowerCase() === 'span') {
                        target = target.closest('button, a') || target;
                    }
    
                    if (!target) {
                        const paneButton = Array.from(dialog.querySelectorAll('.ui-dialog-buttonpane button')).find(isVisible);
                        target = paneButton || null;
                    }
    
                    if (!target) {
                        return {
                            clicked: false,
                            reason: 'No visible Save candidate found',
                            dialogText: (dialog.innerText || dialog.textContent || '').trim().slice(0, 500),
                            buttons: candidates.map(labelFor).filter(Boolean).slice(0, 20)
                        };
                    }
    
                    target.scrollIntoView({block: 'center', inline: 'center'});
                    target.click();
                    return {
                        clicked: true,
                        label: labelFor(target),
                        tag: target.tagName,
                        id: target.id || '',
                        className: target.className || ''
                    };
                    """
                )
                if isinstance(result, dict) and result.get("clicked"):
                    logging.info("Clicked MOSU00 Table Case Entry Save button using DOM fallback: %s", result)
                    return True
                logging.info("MOSU00 Table Case Entry Save DOM fallback did not click: %s", result)
                return False
            except Exception as e:
                logging.info("MOSU00 Table Case Entry Save DOM fallback failed: %s", e)
                return False
    
    def log_mosu00_table_dialog_diagnostics(self):
            try:
                diagnostics = self.driver.execute_script(
                    """
                    const isVisible = (el) => {
                        if (!el) return false;
                        const style = window.getComputedStyle(el);
                        const rect = el.getBoundingClientRect();
                        return style.display !== 'none'
                            && style.visibility !== 'hidden'
                            && style.opacity !== '0'
                            && rect.width > 0
                            && rect.height > 0;
                    };
                    return Array.from(document.querySelectorAll('.ui-dialog, [role="dialog"]'))
                        .filter(isVisible)
                        .map((dialog) => ({
                            id: dialog.id || '',
                            className: dialog.className || '',
                            text: (dialog.innerText || dialog.textContent || '').trim().slice(0, 700),
                            buttons: Array.from(dialog.querySelectorAll('button, input[type="button"], input[type="submit"], a, span.ui-button-text'))
                                .filter(isVisible)
                                .map((button) => ({
                                    tag: button.tagName,
                                    id: button.id || '',
                                    className: button.className || '',
                                    text: (button.innerText || button.textContent || button.value || button.getAttribute('aria-label') || '').trim()
                                }))
                        }))
                        .slice(0, 5);
                    """
                )
                logging.warning("MOSU00 table dialog diagnostics before save failure: %s", diagnostics)
            except Exception as e:
                logging.warning("Could not collect MOSU00 table dialog diagnostics: %s", e)
    
    def accept_mosu00_table_case_save_confirmation(self, expected_count=None):
            try:
                alert = WebDriverWait(self.driver, 6).until(EC.alert_is_present())
                alert_text = alert.text.strip()
                alert.accept()
                logging.info("Accepted MOSU00 table save confirmation alert: %s", alert_text)
                return True
            except TimeoutException:
                pass
            except Exception as e:
                logging.info("MOSU00 table save browser alert check failed: %s", e)
    
            uppercase = "'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'"
            ok_xpaths = [
                (
                    "//div[contains(@class, 'ui-dialog') and "
                    "contains(translate(normalize-space(.), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'SAVE')]"
                    f"//button[.//span[translate(normalize-space(.), {uppercase})='OK'] or translate(normalize-space(.), {uppercase})='OK']"
                ),
                f"//button[.//span[translate(normalize-space(.), {uppercase})='OK'] or translate(normalize-space(.), {uppercase})='OK']",
            ]
    
            for xpath in ok_xpaths:
                try:
                    ok_button = WebDriverWait(self.driver, 6).until(EC.element_to_be_clickable((By.XPATH, xpath)))
                    ok_button.click()
                    logging.info("Accepted MOSU00 table save confirmation popup.")
                    return True
                except Exception:
                    continue
    
            logging.info("No MOSU00 table save confirmation popup was visible.")
            return False

