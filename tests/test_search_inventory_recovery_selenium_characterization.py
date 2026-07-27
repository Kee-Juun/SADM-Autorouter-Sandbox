"""No-driver characterization tests for Search Inventory recovery."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.smducar_router import CaseLawRouter, RouterSessionLostError


def _flow_symbol(name):
    if importlib.util.find_spec(
        "core.router_modes.search_inventory_recovery_selenium"
    ):
        return (
            "core.router_modes.search_inventory_recovery_selenium."
            f"{name}"
        )
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router._raise_if_invalid_session_error = Mock()
    router._close_extra_tabs_and_focus_main = Mock(return_value=True)
    router.safe_alert_accept = Mock()
    router._is_search_inventory_ready = Mock(return_value=True)
    router.click_search_inventory = Mock(return_value=True)
    return router


class SearchInventoryRecoverySeleniumCharacterizationTests(
    unittest.TestCase
):
    def test_readiness_uses_requested_timeout_and_search_field(self):
        router = _router()
        wait = Mock()

        with (
            patch(_flow_symbol("WebDriverWait"), return_value=wait) as wait_type,
            patch(_flow_symbol("EC")) as conditions,
        ):
            expected_condition = object()
            conditions.presence_of_element_located.return_value = (
                expected_condition
            )
            result = CaseLawRouter._is_search_inventory_ready(
                router,
                timeout=12,
            )

        self.assertTrue(result)
        wait_type.assert_called_once_with(router.driver, 12)
        conditions.presence_of_element_located.assert_called_once()
        locator = conditions.presence_of_element_located.call_args.args[0]
        self.assertEqual('//*[@id="documentLNISearch"]', locator[1])
        wait.until.assert_called_once_with(expected_condition)

    def test_readiness_failure_classifies_error_and_returns_false(self):
        router = _router()
        original = RuntimeError("ordinary timeout")
        wait = Mock()
        wait.until.side_effect = original

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            result = CaseLawRouter._is_search_inventory_ready(router)

        self.assertFalse(result)
        router._raise_if_invalid_session_error.assert_called_once_with(
            original,
            "Search Inventory readiness check",
        )

    def test_readiness_propagates_session_loss_from_classifier(self):
        router = _router()
        wait = Mock()
        wait.until.side_effect = RuntimeError("invalid session id")
        router._raise_if_invalid_session_error.side_effect = (
            RouterSessionLostError("lost during readiness")
        )

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            with self.assertRaisesRegex(
                RouterSessionLostError,
                "lost during readiness",
            ):
                CaseLawRouter._is_search_inventory_ready(router)

    def test_refresh_success_preserves_cleanup_alert_and_ready_state_wait(self):
        router = _router()
        wait = Mock()
        manager = Mock()
        manager.attach_mock(
            router._close_extra_tabs_and_focus_main,
            "cleanup",
        )
        manager.attach_mock(router.safe_alert_accept, "alert")
        manager.attach_mock(router.driver.refresh, "refresh")

        with patch(
            _flow_symbol("WebDriverWait"),
            return_value=wait,
        ) as wait_type:
            result = CaseLawRouter.refresh_search_inventory_for_retry(
                router,
                reason="form issue",
            )

        self.assertTrue(result)
        self.assertEqual(
            [call.cleanup(), call.alert(), call.refresh(), call.alert()],
            manager.mock_calls,
        )
        wait_type.assert_called_once_with(router.driver, 25)
        ready_predicate = wait.until.call_args.args[0]
        router.driver.execute_script.return_value = "complete"
        self.assertTrue(ready_predicate(router.driver))
        router.driver.execute_script.assert_called_once_with(
            "return document.readyState"
        )
        router._is_search_inventory_ready.assert_called_once_with(timeout=10)
        router.click_search_inventory.assert_not_called()

    def test_pre_refresh_alert_error_is_classified_then_refresh_continues(self):
        router = _router()
        original = RuntimeError("alert cleanup failed")
        router.safe_alert_accept.side_effect = [original, None]

        with patch(_flow_symbol("WebDriverWait"), return_value=Mock()):
            result = CaseLawRouter.refresh_search_inventory_for_retry(router)

        self.assertTrue(result)
        router._raise_if_invalid_session_error.assert_called_once_with(
            original,
            "pre-refresh alert cleanup",
        )
        router.driver.refresh.assert_called_once_with()

    def test_refresh_error_is_classified_then_readiness_is_checked(self):
        router = _router()
        original = RuntimeError("refresh failed")
        router.driver.refresh.side_effect = original

        result = CaseLawRouter.refresh_search_inventory_for_retry(router)

        self.assertTrue(result)
        router._raise_if_invalid_session_error.assert_called_once_with(
            original,
            "refresh recovery",
        )
        router._is_search_inventory_ready.assert_called_once_with(timeout=10)

    def test_menu_fallback_uses_fifteen_second_readiness_check(self):
        router = _router()
        router._is_search_inventory_ready.side_effect = [False, True]

        with patch(_flow_symbol("WebDriverWait"), return_value=Mock()):
            result = CaseLawRouter.refresh_search_inventory_for_retry(router)

        self.assertTrue(result)
        router.click_search_inventory.assert_called_once_with()
        self.assertEqual(
            [call(timeout=10), call(timeout=15)],
            router._is_search_inventory_ready.call_args_list,
        )

    def test_failed_menu_click_short_circuits_second_readiness_check(self):
        router = _router()
        router._is_search_inventory_ready.return_value = False
        router.click_search_inventory.return_value = False

        with patch(_flow_symbol("WebDriverWait"), return_value=Mock()):
            result = CaseLawRouter.refresh_search_inventory_for_retry(router)

        self.assertFalse(result)
        router.click_search_inventory.assert_called_once_with()
        router._is_search_inventory_ready.assert_called_once_with(timeout=10)

    def test_session_loss_during_pre_refresh_alert_stops_recovery(self):
        router = _router()
        router.safe_alert_accept.side_effect = RuntimeError(
            "invalid session id"
        )
        router._raise_if_invalid_session_error.side_effect = (
            RouterSessionLostError("lost before refresh")
        )

        with self.assertRaisesRegex(
            RouterSessionLostError,
            "lost before refresh",
        ):
            CaseLawRouter.refresh_search_inventory_for_retry(router)

        router.driver.refresh.assert_not_called()
        router._is_search_inventory_ready.assert_not_called()

    @unittest.skipUnless(
        importlib.util.find_spec(
            "core.router_modes.search_inventory_recovery_selenium"
        ),
        "structural boundary applies after extraction",
    )
    def test_router_methods_become_thin_compatibility_entry_points(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))

        for method_name in (
            "_is_search_inventory_ready",
            "refresh_search_inventory_for_retry",
        ):
            with self.subTest(method_name=method_name):
                method = next(
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and node.name == method_name
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
        importlib.util.find_spec(
            "core.router_modes.search_inventory_recovery_selenium"
        ),
        "module boundary applies after extraction",
    )
    def test_extracted_module_excludes_lni_search_and_form_opening(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "search_inventory_recovery_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn('//*[@id="documentLNISearch"]', source)
        self.assertIn("router.click_search_inventory()", source)
        for excluded_term in (
            '//*[@id="search"]',
            "td.searchColumn",
            "handle_lni_search",
            "click_matching_result",
            "open_and_process_form",
        ):
            with self.subTest(excluded_term=excluded_term):
                self.assertNotIn(excluded_term, source)


if __name__ == "__main__":
    unittest.main()
