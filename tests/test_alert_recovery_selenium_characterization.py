"""No-driver characterization tests for shared pending-alert recovery."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import TimeoutException

from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.alert_recovery_selenium"):
        return f"core.router_modes.alert_recovery_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.handle_duplicate_overlay = Mock()
    return router


class AlertRecoverySeleniumCharacterizationTests(unittest.TestCase):
    def test_no_alert_preserves_false_pair_and_initial_timeout(self):
        router = _router()
        wait = Mock()
        wait.until.side_effect = TimeoutException()

        with patch(_flow_symbol("WebDriverWait"), return_value=wait) as wait_type:
            result = CaseLawRouter.accept_pending_alerts(
                router,
                initial_timeout=4,
                followup_timeout=2,
                max_alerts=5,
            )

        self.assertEqual((False, False), result)
        wait_type.assert_called_once_with(router.driver, 4)

    def test_nonduplicate_alert_preserves_accept_sleep_and_followup_timeout(self):
        router = _router()
        alert = Mock()
        alert.text = "Informational alert"
        wait = Mock()
        wait.until.side_effect = [alert, TimeoutException()]

        with (
            patch(_flow_symbol("WebDriverWait"), return_value=wait) as wait_type,
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.accept_pending_alerts(
                router,
                initial_timeout=3,
                followup_timeout=1,
                max_alerts=5,
            )

        self.assertEqual((True, False), result)
        alert.accept.assert_called_once_with()
        sleep.assert_called_once_with(0.25)
        self.assertEqual(
            [call(router.driver, 3), call(router.driver, 1)],
            wait_type.call_args_list,
        )

    def test_duplicate_among_multiple_alerts_preserves_classification(self):
        router = _router()
        alerts = []
        for text in (
            "First alert",
            "Duplicate document detected",
            "Final alert",
        ):
            alert = Mock()
            alert.text = text
            alerts.append(alert)
        wait = Mock()
        wait.until.side_effect = alerts

        with (
            patch(_flow_symbol("WebDriverWait"), return_value=wait),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.accept_pending_alerts(
                router,
                initial_timeout=2,
                followup_timeout=0.5,
                max_alerts=3,
            )

        self.assertEqual((True, True), result)
        for alert in alerts:
            alert.accept.assert_called_once_with()
        self.assertEqual(3, sleep.call_count)

    def test_unexpected_wait_error_preserves_accumulated_state_and_break(self):
        router = _router()
        alert = Mock()
        alert.text = "Accepted first"
        wait = Mock()
        wait.until.side_effect = [alert, RuntimeError("driver issue")]

        with (
            patch(_flow_symbol("WebDriverWait"), return_value=wait),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.accept_pending_alerts(router)

        self.assertEqual((True, False), result)
        alert.accept.assert_called_once_with()
        self.assertEqual(2, wait.until.call_count)

    def test_handle_any_alert_preserves_duplicate_overlay_arguments(self):
        router = _router()
        router.accept_pending_alerts = Mock(return_value=(True, True))

        result = CaseLawRouter.handle_any_alert(
            router,
            timeout=7,
            archive_as_duplicate=True,
        )

        self.assertTrue(result)
        router.accept_pending_alerts.assert_called_once_with(initial_timeout=7)
        router.handle_duplicate_overlay.assert_called_once_with(
            archive_as_duplicate=True
        )

    def test_handle_any_alert_skips_overlay_without_duplicate(self):
        router = _router()
        router.accept_pending_alerts = Mock(return_value=(True, False))

        result = CaseLawRouter.handle_any_alert(router, timeout=2)

        self.assertTrue(result)
        router.handle_duplicate_overlay.assert_not_called()

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.alert_recovery_selenium"),
        "structural boundary applies after extraction",
    )
    def test_router_methods_become_thin_compatibility_entry_points(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))

        for method_name in ("handle_any_alert", "accept_pending_alerts"):
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
        importlib.util.find_spec("core.router_modes.alert_recovery_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_classifies_alerts_without_overlay_ui(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "alert_recovery_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("duplicate document", source)
        self.assertIn("router.handle_duplicate_overlay(", source)
        self.assertNotIn("processDuplicate", source)
        self.assertNotIn("archiveDuplicate", source)
        self.assertNotIn("duplicateContinue", source)


if __name__ == "__main__":
    unittest.main()
