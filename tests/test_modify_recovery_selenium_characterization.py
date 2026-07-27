"""No-driver characterization tests for Modify-mode entry recovery."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import TimeoutException

from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter, RouterSessionLostError


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.modify_recovery_selenium"):
        return f"core.router_modes.modify_recovery_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.check_session_validity = Mock(return_value=True)
    router.handle_duplicate_lni_popup = Mock()
    router._is_invalid_session_error = Mock(return_value=False)
    return router


def _wait(result=None, error=None):
    wait = Mock()
    if error is not None:
        wait.until.side_effect = error
    else:
        wait.until.return_value = result
    return wait


def _alert(text):
    alert = Mock()
    alert.text = text
    return alert


class ModifyRecoverySeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_no_alert_is_success_after_one_modify_click(self):
        router = _router()
        modify_button = Mock()

        with patch(
            _flow_symbol("WebDriverWait"),
            side_effect=[
                _wait(result=modify_button),
                _wait(error=TimeoutException()),
            ],
        ) as wait_type:
            result = CaseLawRouter.attempt_open_modify(
                router,
                file_path="unused.xlsx",
                row_index=10,
                max_attempts=3,
            )

        self.assertTrue(result)
        modify_button.click.assert_called_once_with()
        self.assertEqual(
            [call(router.driver, 120), call(router.driver, 5)],
            wait_type.call_args_list,
        )
        self.assertNotIn(10, status_updates_buffer)

    def test_ready_alert_retries_after_exact_five_second_pause(self):
        router = _router()
        first_button = Mock()
        second_button = Mock()
        ready_alert = _alert("Ready To Process = [ON]")

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=first_button),
                    _wait(result=ready_alert),
                    _wait(result=second_button),
                    _wait(error=TimeoutException()),
                ],
            ),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.attempt_open_modify(router, max_attempts=2)

        self.assertTrue(result)
        first_button.click.assert_called_once_with()
        second_button.click.assert_called_once_with()
        ready_alert.accept.assert_called_once_with()
        sleep.assert_called_once_with(5)

    def test_duplicate_document_alert_delegates_popup_and_succeeds(self):
        router = _router()
        duplicate_alert = _alert("Duplicate Document found")

        with patch(
            _flow_symbol("WebDriverWait"),
            side_effect=[
                _wait(result=Mock()),
                _wait(result=duplicate_alert),
            ],
        ):
            result = CaseLawRouter.attempt_open_modify(router)

        self.assertTrue(result)
        duplicate_alert.accept.assert_called_once_with()
        router.handle_duplicate_lni_popup.assert_called_once_with()

    def test_dsar_then_duplicate_accepts_both_and_delegates_popup(self):
        router = _router()
        dsar_alert = _alert("DSAR duplicate warning")
        document_alert = _alert("Duplicate document warning")

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(result=dsar_alert),
                    _wait(result=document_alert),
                ],
            ),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.attempt_open_modify(router)

        self.assertTrue(result)
        dsar_alert.accept.assert_called_once_with()
        document_alert.accept.assert_called_once_with()
        sleep.assert_called_once_with(2)
        router.handle_duplicate_lni_popup.assert_called_once_with()

    def test_exhausted_non_session_errors_preserve_sleep_and_status(self):
        router = _router()
        failures = [
            _wait(error=RuntimeError("not clickable 1")),
            _wait(error=RuntimeError("not clickable 2")),
        ]

        with (
            patch(_flow_symbol("WebDriverWait"), side_effect=failures),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.attempt_open_modify(
                router,
                row_index=20,
                max_attempts=2,
            )

        self.assertFalse(result)
        self.assertEqual("ERROR: MODIFY FAILED", status_updates_buffer[20])
        self.assertEqual([call(2), call(2)], sleep.call_args_list)
        self.assertEqual(2, router._is_invalid_session_error.call_count)

    def test_exhausted_failure_without_row_index_writes_no_status(self):
        router = _router()

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                return_value=_wait(error=RuntimeError("not clickable")),
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.attempt_open_modify(
                router,
                row_index=None,
                max_attempts=1,
            )

        self.assertFalse(result)
        self.assertEqual({}, status_updates_buffer)

    def test_invalid_precheck_is_retried_and_returns_false_under_legacy_policy(self):
        router = _router()
        router.check_session_validity.return_value = False

        with (
            patch(_flow_symbol("WebDriverWait")) as wait_type,
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.attempt_open_modify(
                router,
                row_index=30,
            )

        self.assertFalse(result)
        self.assertEqual("ERROR: MODIFY FAILED", status_updates_buffer[30])
        self.assertEqual(3, router.check_session_validity.call_count)
        wait_type.assert_not_called()
        self.assertEqual([call(2), call(2), call(2)], sleep.call_args_list)

    def test_invalid_driver_error_preserves_translation_and_cause(self):
        router = _router()
        original = RuntimeError("invalid session id")
        router._is_invalid_session_error.return_value = True

        with patch(
            _flow_symbol("WebDriverWait"),
            return_value=_wait(error=original),
        ):
            with self.assertRaisesRegex(
                RouterSessionLostError,
                "lost while opening Modify mode",
            ) as raised:
                CaseLawRouter.attempt_open_modify(router)

        self.assertIs(original, raised.exception.__cause__)

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.modify_recovery_selenium"),
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
            and node.name == "attempt_open_modify"
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
        importlib.util.find_spec("core.router_modes.modify_recovery_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_excludes_search_and_duplicate_overlay_ui(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "modify_recovery_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn('//*[@id="modify"]', source)
        self.assertIn("router.handle_duplicate_lni_popup()", source)
        for excluded_term in (
            "documentLNISearch",
            "click_search_inventory",
            "processDuplicate",
            "archiveDuplicate",
            "duplicateContinue",
        ):
            with self.subTest(excluded_term=excluded_term):
                self.assertNotIn(excluded_term, source)


if __name__ == "__main__":
    unittest.main()
