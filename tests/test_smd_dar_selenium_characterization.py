"""No-driver characterization tests for the shared SMD/DAR form flow."""

import importlib.util
import ast
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.smd_dar_selenium"):
        return f"core.router_modes.smd_dar_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router_with_interactable_form():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.prepare_common_fields = Mock()
    router.handle_any_alert = Mock()
    router.handle_counsel_fields = Mock()
    router.handle_main_opinion_fields = Mock()
    router.click_ready_checkbox_and_check_overlay = Mock(return_value=False)
    router.handle_routing_and_save = Mock(return_value="DONE")
    router.get_decision_date_from_received = Mock(return_value=None)
    router.extract_decision_date_from_filename = Mock(return_value=None)
    router.find_main_opinion_date_for_counsel = Mock(return_value=None)
    router.open_lni_in_irt_tab = Mock()
    comments = Mock()
    comments.is_enabled.return_value = True
    route = Mock()
    route.is_enabled.return_value = True
    router.wait = Mock()
    router.wait.until.side_effect = [comments, route]
    router.driver = Mock()
    router.driver.window_handles = ["main"]
    return router, route


def _run_success_flow(
    router,
    route,
    row,
    *,
    row_index,
    dar_mode=False,
    ready_result=False,
    counsel=False,
):
    clickable_wait = Mock()
    clickable_wait.until.return_value = route
    dropdown = Mock()
    router.click_ready_checkbox_and_check_overlay.return_value = ready_result

    with ExitStack() as stack:
        is_counsel = stack.enter_context(
            patch("core.smducar_router.is_counsel", return_value=counsel)
        )
        webdriver_wait = stack.enter_context(patch(_flow_symbol("WebDriverWait")))
        select = stack.enter_context(patch(_flow_symbol("Select")))
        webdriver_wait.return_value = clickable_wait
        select.return_value = dropdown
        result = CaseLawRouter.fill_irt_form(
            router,
            row,
            [{"FileName": row["FileName"]}],
            row_index,
            "mapping.xlsx",
            dar_mode=dar_mode,
        )

    return result, is_counsel, dropdown


class SMDDARSeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_main_manual_date_preserves_field_route_and_save_call_trace(self):
        router, route = _router_with_interactable_form()
        row = {
            "FileName": "main_opinion_20260101.pdf",
            "LNI": "LNI-MAIN",
            "Decision Date": "03-04-2026",
        }

        result, is_counsel, dropdown = _run_success_flow(
            router,
            route,
            row,
            row_index=60,
        )
        self.assertEqual("DONE", result)
        router.prepare_common_fields.assert_called_once_with(
            "main_opinion_20260101.pdf",
            "03-04-2026",
            False,
            False,
        )
        router.handle_main_opinion_fields.assert_called_once_with(
            row,
            [{"FileName": row["FileName"]}],
            60,
            "mapping.xlsx",
            False,
            False,
        )
        router.handle_counsel_fields.assert_not_called()
        dropdown.select_by_visible_text.assert_called_once_with("Outside Conversion")
        router.click_ready_checkbox_and_check_overlay.assert_called_once_with(False)
        router.handle_routing_and_save.assert_called_once_with(
            False,
            60,
            skip_route_and_ready=True,
        )
        self.assertEqual(
            [call(), call(), call(), call(), call(), call()],
            router.handle_any_alert.call_args_list,
        )

    def test_dar_counsel_preserves_main_date_archive_and_counsel_fields(self):
        router, route = _router_with_interactable_form()
        router.find_main_opinion_date_for_counsel.return_value = "02-03-2026"
        row = {
            "FileName": "dar_counsel.pdf",
            "LNI": "LNI-COUNSEL",
            "Decision Date": None,
        }
        clickable_wait = Mock()
        clickable_wait.until.return_value = route
        dropdown = Mock()

        with ExitStack() as stack:
            stack.enter_context(
                patch("core.smducar_router.is_counsel", return_value=True)
            )
            format_docket = stack.enter_context(
                patch.object(
                    CaseLawRouter,
                    "format_docket_number",
                    return_value="DAR-123",
                )
            )
            webdriver_wait = stack.enter_context(
                patch(_flow_symbol("WebDriverWait"))
            )
            select = stack.enter_context(patch(_flow_symbol("Select")))
            webdriver_wait.return_value = clickable_wait
            select.return_value = dropdown
            result = CaseLawRouter.fill_irt_form(
                router,
                row,
                [row],
                61,
                "mapping.xlsx",
                dar_mode=True,
            )

        self.assertEqual("DONE", result)
        format_docket.assert_called_once_with(None, "dar_counsel.pdf", True, False)
        router.find_main_opinion_date_for_counsel.assert_called_once_with(
            "DAR-123",
            "dar_counsel.pdf",
            True,
            False,
        )
        router.prepare_common_fields.assert_called_once_with(
            "dar_counsel.pdf",
            "02-03-2026",
            True,
            False,
        )
        router.handle_counsel_fields.assert_called_once_with(row, True, False)
        router.handle_main_opinion_fields.assert_not_called()
        dropdown.select_by_visible_text.assert_called_once_with("Archive")
        router.click_ready_checkbox_and_check_overlay.assert_called_once_with(True)
        router.handle_routing_and_save.assert_called_once_with(
            True,
            61,
            skip_route_and_ready=True,
        )

    def test_received_date_remains_final_fallback(self):
        router, route = _router_with_interactable_form()
        router.get_decision_date_from_received.return_value = "01-31-2026"
        row = {
            "FileName": "main_without_date.pdf",
            "LNI": "LNI-FALLBACK",
            "Decision Date": "",
        }

        result, _, _ = _run_success_flow(
            router,
            route,
            row,
            row_index=62,
        )

        self.assertEqual("DONE", result)
        router.extract_decision_date_from_filename.assert_called_once_with(
            "main_without_date.pdf"
        )
        router.get_decision_date_from_received.assert_called_once_with()
        router.prepare_common_fields.assert_called_once_with(
            "main_without_date.pdf",
            "01-31-2026",
            False,
            False,
        )

    def test_ready_outcomes_preserve_terminal_results_and_statuses(self):
        cases = [
            ("ROUTE_ERROR", "ROUTE ERROR", None),
            ("ALERT_HANDLED", "ALERT_HANDLED", None),
            ("READY_NOT_CLICKABLE", "ALREADY PROCESSED", "ALREADY PROCESSED"),
        ]
        for offset, (ready_result, expected, expected_status) in enumerate(cases):
            with self.subTest(ready_result=ready_result):
                router, route = _router_with_interactable_form()
                row_index = 63 + offset
                result, _, _ = _run_success_flow(
                    router,
                    route,
                    {
                        "FileName": "main_opinion.pdf",
                        "LNI": "LNI-READY",
                        "Decision Date": "01-01-2026",
                    },
                    row_index=row_index,
                    ready_result=ready_result,
                )

                self.assertEqual(expected, result)
                self.assertEqual(expected_status, status_updates_buffer.get(row_index))
                router.handle_routing_and_save.assert_not_called()
                router.driver.close.assert_called_once_with()
                router.driver.switch_to.window.assert_called_once_with("main")

    def test_counsel_noninteractable_form_retries_before_success(self):
        router, route = _router_with_interactable_form()
        disabled_comments = Mock()
        disabled_comments.is_enabled.return_value = False
        disabled_route = Mock()
        disabled_route.is_enabled.return_value = False
        enabled_comments = Mock()
        enabled_comments.is_enabled.return_value = True
        route.is_enabled.return_value = True
        router.wait.until.side_effect = [
            disabled_comments,
            disabled_route,
            enabled_comments,
            route,
        ]
        row = {
            "FileName": "counsel_retry.pdf",
            "LNI": "LNI-RETRY",
            "Decision Date": "01-01-2026",
        }
        clickable_wait = Mock()
        clickable_wait.until.return_value = route

        with ExitStack() as stack:
            stack.enter_context(
                patch("core.smducar_router.is_counsel", return_value=True)
            )
            webdriver_wait = stack.enter_context(
                patch(_flow_symbol("WebDriverWait"))
            )
            stack.enter_context(patch(_flow_symbol("Select")))
            webdriver_wait.return_value = clickable_wait
            result = CaseLawRouter.fill_irt_form(
                router,
                row,
                [row],
                66,
                "mapping.xlsx",
            )

        self.assertEqual("DONE", result)
        self.assertEqual(2, router.handle_counsel_fields.call_count)
        router.open_lni_in_irt_tab.assert_called_once_with(row)
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    def test_router_keeps_dispatch_and_error_boundary_but_not_shared_flow(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        source = router_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "fill_irt_form"
        )
        method_source = ast.get_source_segment(source, method)

        self.assertIn("select_form_mode_handler", method_source)
        self.assertIn("run_smd_dar_irt_form", method_source)
        self.assertIn('row["LNI"]', method_source)
        self.assertNotIn("handle_counsel_fields", method_source)
        self.assertNotIn("handle_main_opinion_fields", method_source)
        self.assertNotIn("Outside Conversion", method_source)
        self.assertNotIn('"Archive"', method_source)

    def test_extracted_module_contains_only_shared_smd_dar_flow(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "smd_dar_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("handle_counsel_fields", source)
        self.assertIn("handle_main_opinion_fields", source)
        self.assertIn("Outside Conversion", source)
        self.assertIn("Archive", source)
        for specialized_mode in ("MSPB", "ITC", "IRSPLR", "OHTAX0", "MNSUTB"):
            with self.subTest(specialized_mode=specialized_mode):
                self.assertNotIn(specialized_mode, source)


if __name__ == "__main__":
    unittest.main()
