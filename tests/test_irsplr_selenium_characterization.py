"""No-driver characterization tests for the current IRSPLR form flow."""

import ast
import importlib.util
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.irsplr_extractor import IRSPLRMetadata
from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _selenium_symbol(name):
    if importlib.util.find_spec("core.router_modes.irsplr_selenium"):
        return f"core.router_modes.irsplr_selenium.{name}"
    return f"core.smducar_router.{name}"


def _metadata(*, excluded=False, text_fallback=False):
    return IRSPLRMetadata(
        court="FDPLR000",
        docket_number="2026-1",
        decision_date="01-02-2026",
        source_detail="Excluded" if excluded else "Private Letter Ruling",
        is_excluded=excluded,
        exclusion_reason="Excluded filename" if excluded else "",
        is_text_fallback=text_fallback,
    )


class IRSPLRSeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_missing_metadata_preserves_skip_status(self):
        router = CaseLawRouter.__new__(CaseLawRouter)

        result = CaseLawRouter.fill_irsplr_irt_form(
            router,
            {"FileName": "2026001.pdf"},
            38,
            None,
        )

        self.assertEqual("SKIPPED: IRSPLR PDF DATA NOT FOUND", result)
        self.assertEqual(
            "SKIPPED: IRSPLR PDF DATA NOT FOUND",
            status_updates_buffer[38],
        )

    def test_text_fallback_preserves_already_processed_and_ocr_paths(self):
        for already_processed, expected in (
            (True, "ALREADY PROCESSED"),
            (False, "SKIPPED: IRSPLR OCR REQUIRED"),
        ):
            with self.subTest(already_processed=already_processed):
                status_updates_buffer.clear()
                router = CaseLawRouter.__new__(CaseLawRouter)
                router.is_irt_form_already_processed = Mock(
                    return_value=already_processed
                )
                router.driver = Mock()
                router.driver.window_handles = ["main"]

                result = CaseLawRouter.fill_irsplr_irt_form(
                    router,
                    {"FileName": "2026001.pdf"},
                    39,
                    _metadata(text_fallback=True),
                )

                self.assertEqual(expected, result)
                self.assertEqual(expected, status_updates_buffer[39])
                router.driver.close.assert_called_once_with()
                router.driver.switch_to.window.assert_called_once_with("main")

    def test_locked_excluded_form_remains_already_processed(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.is_locked_archive_excluded_form = Mock(return_value=True)
        router.driver = Mock()
        router.driver.window_handles = ["main"]
        metadata = _metadata(excluded=True)
        row = {"FileName": "2026001.pdf"}

        result = CaseLawRouter.fill_irsplr_irt_form(
            router,
            row,
            40,
            metadata,
        )

        self.assertEqual("ALREADY PROCESSED", result)
        self.assertEqual("ALREADY PROCESSED", status_updates_buffer[40])
        router.is_locked_archive_excluded_form.assert_called_once_with("IRSPLR")
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    def test_enabled_route_preserves_normal_and_excluded_route_labels(self):
        for excluded, expected_route in (
            (False, "Outside Conversion"),
            (True, "Archive"),
        ):
            with self.subTest(excluded=excluded):
                router = CaseLawRouter.__new__(CaseLawRouter)
                router.prepare_common_fields = Mock()
                router.handle_any_alert = Mock()
                router.is_locked_archive_excluded_form = Mock(return_value=False)
                router.handle_irsplr_fields = Mock(return_value=True)
                router.click_ready_checkbox_and_check_overlay = Mock(
                    return_value=False
                )
                router.handle_routing_and_save = Mock(return_value="DONE")
                comments = Mock()
                comments.is_enabled.return_value = True
                route = Mock()
                route.is_enabled.return_value = True
                router.wait = Mock()
                router.wait.until.side_effect = [comments, route, route]
                router.driver = Mock()
                clickable_wait = Mock()
                clickable_wait.until.return_value = route
                dropdown = Mock()
                metadata = _metadata(excluded=excluded)
                row = {"FileName": "2026001.pdf"}

                with ExitStack() as stack:
                    webdriver_wait = stack.enter_context(
                        patch(_selenium_symbol("WebDriverWait"))
                    )
                    select = stack.enter_context(
                        patch(_selenium_symbol("Select"))
                    )
                    webdriver_wait.return_value = clickable_wait
                    select.return_value = dropdown
                    result = CaseLawRouter.fill_irsplr_irt_form(
                        router,
                        row,
                        41,
                        metadata,
                    )

                self.assertEqual("DONE", result)
                router.prepare_common_fields.assert_called_once_with(
                    "2026001.pdf",
                    decision_date="01-02-2026",
                    dar_mode=False,
                    wc_mode=False,
                    docket_override="2026-1",
                    court="FDPLR000",
                )
                router.handle_irsplr_fields.assert_called_once_with(row, metadata)
                dropdown.select_by_visible_text.assert_called_once_with(
                    expected_route
                )
                router.driver.execute_script.assert_called_once_with(
                    "document.getElementById('route').dispatchEvent(new Event('change'))"
                )
                router.click_ready_checkbox_and_check_overlay.assert_called_once_with(
                    False
                )
                router.handle_routing_and_save.assert_called_once_with(
                    False,
                    41,
                    skip_route_and_ready=True,
                )
                self.assertEqual(
                    [call(), call(), call(), call(), call()],
                    router.handle_any_alert.call_args_list,
                )

    def test_disabled_excluded_route_preserves_confirmed_archive_path(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.is_locked_archive_excluded_form = Mock(return_value=False)
        router.handle_irsplr_fields = Mock(return_value=True)
        router.get_selected_dropdown_text = Mock(return_value="Archive")
        router.dropdown_text_matches = Mock(return_value=True)
        router.set_dropdown_by_visible_text = Mock()
        router.click_ready_checkbox_and_check_overlay = Mock(return_value=False)
        router.handle_routing_and_save = Mock(return_value="DONE")
        comments = Mock()
        comments.is_enabled.return_value = True
        route = Mock()
        route.is_enabled.return_value = False
        router.wait = Mock()
        router.wait.until.side_effect = [comments, route, route]
        router.driver = Mock()
        metadata = _metadata(excluded=True)

        result = CaseLawRouter.fill_irsplr_irt_form(
            router,
            {"FileName": "2026001.pdf"},
            42,
            metadata,
        )

        self.assertEqual("DONE", result)
        self.assertEqual(2, router.get_selected_dropdown_text.call_count)
        router.dropdown_text_matches.assert_called_once_with("Archive", "Archive")
        router.set_dropdown_by_visible_text.assert_not_called()
        router.handle_routing_and_save.assert_called_once_with(
            False,
            42,
            skip_route_and_ready=True,
        )
        self.assertEqual(
            [call(), call()],
            router.handle_any_alert.call_args_list,
        )

    def test_case_law_router_keeps_only_the_compatibility_entry_point(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "fill_irsplr_irt_form"
        )
        executable_body = [
            statement
            for statement in method.body
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ]

        self.assertEqual(1, len(executable_body))
        self.assertIsInstance(executable_body[0], ast.Return)

    def test_extracted_module_contains_only_irsplr_mode_flow(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "irsplr_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("Outside Conversion", source)
        self.assertIn("Archive", source)
        self.assertIn("IRSPLR OCR REQUIRED", source)
        for other_mode in ("MSPB", "Selected ITC", "OHTAX0", "MNSUTB"):
            with self.subTest(other_mode=other_mode):
                self.assertNotIn(other_mode, source)


if __name__ == "__main__":
    unittest.main()
