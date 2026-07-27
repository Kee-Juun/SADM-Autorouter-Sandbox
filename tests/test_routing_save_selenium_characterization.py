"""No-driver characterization tests for final routing and save handling."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import (
    TimeoutException,
    UnexpectedAlertPresentException,
)

from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.routing_save_selenium"):
        return f"core.router_modes.routing_save_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.driver.window_handles = ["main"]
    router.handle_any_alert = Mock()
    router.handle_unexpected_alert = Mock(return_value=False)
    router.handle_duplicate_overlay = Mock()
    router.click_ready_checkbox_and_check_overlay = Mock(return_value=False)
    router.click_element = Mock()
    router.attempt_open_modify = Mock()
    return router


class RoutingSaveSeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_skip_route_and_ready_preserves_direct_save_success(self):
        router = _router()
        wait = Mock()
        wait.until.side_effect = TimeoutException()

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            result = CaseLawRouter.handle_routing_and_save(
                router,
                False,
                70,
                skip_route_and_ready=True,
            )

        self.assertEqual("DONE", result)
        router.click_element.assert_called_once_with('//*[@id="add"]')
        router.driver.find_element.assert_not_called()
        router.click_ready_checkbox_and_check_overlay.assert_not_called()
        router.handle_any_alert.assert_not_called()

    def test_route_and_ready_preserve_main_and_counsel_labels(self):
        for is_counsel, expected_route in (
            (False, "Outside Conversion"),
            (True, "Archive"),
        ):
            with self.subTest(is_counsel=is_counsel):
                router = _router()
                route = Mock()
                router.driver.find_element.return_value = route
                router.click_ready_checkbox_and_check_overlay.return_value = (
                    "READY_NOT_CLICKABLE"
                )
                dropdown = Mock()

                with patch(_flow_symbol("Select"), return_value=dropdown):
                    result = CaseLawRouter.handle_routing_and_save(
                        router,
                        is_counsel,
                        71,
                    )

                self.assertEqual("ALREADY PROCESSED", result)
                self.assertEqual(
                    "ALREADY PROCESSED",
                    status_updates_buffer[71],
                )
                dropdown.select_by_visible_text.assert_called_once_with(
                    expected_route
                )
                router.driver.execute_script.assert_has_calls(
                    [
                        call(
                            "arguments[0].scrollIntoView(true);",
                            route,
                        ),
                        call(
                            "document.getElementById('route').dispatchEvent("
                            "new Event('change'))"
                        ),
                    ]
                )
                router.handle_any_alert.assert_has_calls(
                    [call(timeout=2), call(timeout=2)]
                )
                router.driver.close.assert_called_once_with()
                router.driver.switch_to.window.assert_called_once_with("main")
                router.click_element.assert_not_called()
                status_updates_buffer.clear()

    def test_unexpected_alert_during_route_click_preserves_retry_path(self):
        router = _router()
        route = Mock()
        route.click.side_effect = [
            UnexpectedAlertPresentException(),
            None,
        ]
        router.driver.find_element.return_value = route
        dropdown = Mock()
        wait = Mock()
        wait.until.side_effect = TimeoutException()

        with (
            patch(_flow_symbol("Select"), return_value=dropdown),
            patch(_flow_symbol("WebDriverWait"), return_value=wait),
        ):
            result = CaseLawRouter.handle_routing_and_save(
                router,
                False,
                72,
            )

        self.assertEqual("DONE", result)
        self.assertEqual(2, router.driver.find_element.call_count)
        self.assertEqual(2, route.click.call_count)
        dropdown.select_by_visible_text.assert_called_once_with(
            "Outside Conversion"
        )
        router.handle_any_alert.assert_has_calls(
            [call(timeout=2), call(), call(timeout=2), call(timeout=2)]
        )
        router.click_element.assert_called_once_with('//*[@id="add"]')

    def test_invalid_routing_combo_preserves_three_attempt_retry_contract(self):
        router = _router()
        alert = Mock()
        alert.text = (
            "Route = [ARC] VendorCode = [ARC] Workflow = [] "
            "is not a valid routing combo"
        )
        router.driver.switch_to.alert = alert
        wait = Mock()
        wait.until.return_value = alert

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            result = CaseLawRouter.handle_routing_and_save(
                router,
                True,
                73,
                skip_route_and_ready=True,
            )

        self.assertEqual("INVALID ROUTING COMBO", result)
        self.assertEqual("INVALID ROUTING COMBO", status_updates_buffer[73])
        self.assertEqual(3, router.click_element.call_count)
        self.assertEqual(3, alert.accept.call_count)
        self.assertEqual(3, router.driver.close.call_count)
        self.assertEqual(
            [call(row_index=73), call(row_index=73)],
            router.attempt_open_modify.call_args_list,
        )

    def test_save_exception_preserves_already_processed_cleanup(self):
        router = _router()
        router.click_element.side_effect = RuntimeError("save failed")

        result = CaseLawRouter.handle_routing_and_save(
            router,
            False,
            74,
            skip_route_and_ready=True,
        )

        self.assertEqual("ALREADY PROCESSED", result)
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.routing_save_selenium"),
        "structural boundary applies after extraction",
    )
    def test_router_method_becomes_thin_compatibility_entry_point(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "handle_routing_and_save"
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

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.routing_save_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_remains_mode_neutral(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "routing_save_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("Outside Conversion", source)
        self.assertIn("Archive", source)
        self.assertIn("INVALID ROUTING COMBO", source)
        self.assertIn("READY_NOT_CLICKABLE", source)
        for mode_name in ("MSPB", "ITC", "IRSPLR", "OHTAX0", "MNSUTB"):
            with self.subTest(mode_name=mode_name):
                self.assertNotIn(mode_name, source)


if __name__ == "__main__":
    unittest.main()
