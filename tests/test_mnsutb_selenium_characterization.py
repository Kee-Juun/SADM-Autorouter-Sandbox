"""No-driver characterization tests for the current MNSUTB form flow."""

import ast
import importlib.util
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.mnsutb_extractor import MNSUTBMetadata, MNSUTB_SOURCE_DETAIL
from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _selenium_symbol(name):
    if importlib.util.find_spec("core.router_modes.mnsutb_selenium"):
        return f"core.router_modes.mnsutb_selenium.{name}"
    return f"core.smducar_router.{name}"


class MNSUTBSeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_missing_metadata_preserves_skip_status(self):
        router = CaseLawRouter.__new__(CaseLawRouter)

        result = CaseLawRouter.fill_mnsutb_irt_form(
            router,
            {"FileName": "LDC_SMD_A24-12345.pdf"},
            18,
            None,
        )

        self.assertEqual("SKIPPED: MNSUTB PDF DATA NOT FOUND", result)
        self.assertEqual(
            "SKIPPED: MNSUTB PDF DATA NOT FOUND",
            status_updates_buffer[18],
        )

    def test_disabled_route_with_enabled_comments_remains_already_processed(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.handle_mnsutb_fields = Mock(return_value=True)
        comments = Mock()
        comments.is_enabled.return_value = True
        route = Mock()
        route.is_enabled.return_value = False
        router.wait = Mock()
        router.wait.until.side_effect = [comments, route]
        router.driver = Mock()
        router.driver.window_handles = ["main"]
        metadata = MNSUTBMetadata(
            court="STMNSUTB",
            docket_number="A24-12345",
            decision_date="01-02-2026",
            source_detail=MNSUTB_SOURCE_DETAIL,
        )

        result = CaseLawRouter.fill_mnsutb_irt_form(
            router,
            {"FileName": "LDC_SMD_A24-12345.pdf"},
            19,
            metadata,
        )

        self.assertEqual("ALREADY PROCESSED", result)
        self.assertEqual("ALREADY PROCESSED", status_updates_buffer[19])
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    def test_success_path_preserves_route_and_save_call_trace(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.handle_mnsutb_fields = Mock(return_value=True)
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
        metadata = MNSUTBMetadata(
            court="STMNSUTB",
            docket_number="A24-12345",
            decision_date="01-02-2026",
            source_detail=MNSUTB_SOURCE_DETAIL,
        )
        row = {"FileName": "LDC_SMD_A24-12345.pdf"}

        with ExitStack() as stack:
            webdriver_wait = stack.enter_context(
                patch(_selenium_symbol("WebDriverWait"))
            )
            select = stack.enter_context(patch(_selenium_symbol("Select")))
            webdriver_wait.return_value = clickable_wait
            select.return_value = dropdown
            result = CaseLawRouter.fill_mnsutb_irt_form(
                router,
                row,
                20,
                metadata,
            )

        self.assertEqual("DONE", result)
        router.prepare_common_fields.assert_called_once_with(
            "LDC_SMD_A24-12345.pdf",
            decision_date="01-02-2026",
            dar_mode=False,
            wc_mode=False,
            docket_override="A24-12345",
            court=None,
        )
        router.handle_mnsutb_fields.assert_called_once_with(row, metadata)
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
            20,
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
            if isinstance(node, ast.FunctionDef)
            and node.name == "fill_mnsutb_irt_form"
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

    def test_extracted_module_contains_only_mnsutb_mode_flow(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "mnsutb_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("Outside Conversion", source)
        self.assertIn('//*[@id="route"]', source)
        for other_mode in ("MSPB", "ITC route", "IRSPLR", "OHTAX0"):
            with self.subTest(other_mode=other_mode):
                self.assertNotIn(other_mode, source)


if __name__ == "__main__":
    unittest.main()
