"""No-driver characterization tests for the current OHTAX0 form flow."""

import ast
import importlib.util
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.ohtax0_extractor import OHTAX0Metadata
from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _selenium_symbol(name):
    if importlib.util.find_spec("core.router_modes.ohtax0_selenium"):
        return f"core.router_modes.ohtax0_selenium.{name}"
    return f"core.smducar_router.{name}"


class OHTAX0SeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_missing_metadata_preserves_skip_status(self):
        router = CaseLawRouter.__new__(CaseLawRouter)

        result = CaseLawRouter.fill_ohtax0_irt_form(
            router,
            {"FileName": "saq1_2026_1.pdf"},
            8,
            None,
        )

        self.assertEqual("SKIPPED: OHTAX0 PDF DATA NOT FOUND", result)
        self.assertEqual(
            "SKIPPED: OHTAX0 PDF DATA NOT FOUND",
            status_updates_buffer[8],
        )

    def test_disabled_route_with_enabled_comments_remains_already_processed(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.handle_ohtax0_fields = Mock(return_value=True)
        comments = Mock()
        comments.is_enabled.return_value = True
        route = Mock()
        route.is_enabled.return_value = False
        router.wait = Mock()
        router.wait.until.side_effect = [comments, route]
        router.driver = Mock()
        router.driver.window_handles = ["main"]
        metadata = OHTAX0Metadata(
            court="STOHTAX0",
            docket_number="2026-1",
            decision_date="01-02-2026",
            source_detail="Final Decision",
        )

        result = CaseLawRouter.fill_ohtax0_irt_form(
            router,
            {"FileName": "saq1_2026_1.pdf"},
            9,
            metadata,
        )

        self.assertEqual("ALREADY PROCESSED", result)
        self.assertEqual("ALREADY PROCESSED", status_updates_buffer[9])
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    def test_success_path_preserves_route_and_save_call_trace(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.handle_ohtax0_fields = Mock(return_value=True)
        router.click_ready_checkbox_and_check_overlay = Mock(return_value=False)
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
        metadata = OHTAX0Metadata(
            court="STOHTAX0",
            docket_number="2026-1",
            decision_date="01-02-2026",
            source_detail="Final Decision",
        )
        row = {"FileName": "saq1_2026_1.pdf"}

        with ExitStack() as stack:
            webdriver_wait = stack.enter_context(
                patch(_selenium_symbol("WebDriverWait"))
            )
            select = stack.enter_context(patch(_selenium_symbol("Select")))
            webdriver_wait.return_value = clickable_wait
            select.return_value = dropdown
            result = CaseLawRouter.fill_ohtax0_irt_form(
                router,
                row,
                10,
                metadata,
            )

        self.assertEqual("DONE", result)
        router.prepare_common_fields.assert_called_once_with(
            "saq1_2026_1.pdf",
            decision_date="01-02-2026",
            dar_mode=False,
            wc_mode=False,
            docket_override="2026-1",
            court="STOHTAX0",
        )
        router.handle_ohtax0_fields.assert_called_once_with(row, metadata)
        route.click.assert_called_once_with()
        dropdown.select_by_visible_text.assert_called_once_with(
            "Outside Conversion"
        )
        router.driver.execute_script.assert_called_once_with(
            "document.getElementById('route').dispatchEvent(new Event('change'))"
        )
        router.click_ready_checkbox_and_check_overlay.assert_called_once_with(False)
        router.handle_routing_and_save.assert_called_once_with(
            False,
            10,
            skip_route_and_ready=True,
        )
        self.assertEqual(
            [call(), call(), call(), call(), call()],
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
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "fill_ohtax0_irt_form"
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

    def test_extracted_module_contains_only_ohtax0_mode_flow(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "ohtax0_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("Outside Conversion", source)
        self.assertIn('//*[@id="route"]', source)
        for other_mode in ("MSPB", "ITC route", "IRSPLR", "MNSUTB"):
            with self.subTest(other_mode=other_mode):
                self.assertNotIn(other_mode, source)


if __name__ == "__main__":
    unittest.main()
