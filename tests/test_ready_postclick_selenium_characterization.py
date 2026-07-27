"""No-driver characterization tests for Ready/post-click handling."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import TimeoutException

from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec(
        "core.router_modes.ready_postclick_selenium"
    ):
        return f"core.router_modes.ready_postclick_selenium.{name}"
    return f"core.smducar_router.{name}"


def _wait(result=None, error=None, until_not_error=None):
    wait = Mock()
    if error is not None:
        wait.until.side_effect = error
    else:
        wait.until.return_value = result
    if until_not_error is not None:
        wait.until_not.side_effect = until_not_error
    return wait


def _alert(text):
    alert = Mock()
    alert.text = text
    return alert


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.handle_any_alert = Mock(return_value=False)
    router.handle_duplicate_lni_popup = Mock()
    router.handle_duplicate_overlay = Mock()
    router.click_element = Mock()
    return router


class ReadyPostclickSeleniumCharacterizationTests(unittest.TestCase):
    def test_first_click_no_alert_or_overlay_returns_false(self):
        router = _router()
        ready = Mock()

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=ready),
                    _wait(error=TimeoutException()),
                    _wait(error=TimeoutException()),
                ],
            ) as wait_type,
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router,
                is_counsel=False,
            )

        self.assertFalse(result)
        ready.click.assert_called_once_with()
        router.driver.execute_script.assert_called_once_with(
            "arguments[0].scrollIntoView({block: 'center'});",
            ready,
        )
        sleep.assert_called_once_with(0.25)
        router.handle_any_alert.assert_called_once_with(timeout=2)
        self.assertEqual(
            [
                call(router.driver, 5),
                call(router.driver, 2),
                call(router.driver, 3),
            ],
            wait_type.call_args_list,
        )

    def test_first_click_failure_retries_after_alert_and_one_second(self):
        router = _router()
        ready = Mock()

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(error=RuntimeError("not clickable")),
                    _wait(result=ready),
                    _wait(error=TimeoutException()),
                    _wait(error=TimeoutException()),
                ],
            ),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertFalse(result)
        self.assertEqual(
            [call(timeout=1), call(timeout=2)],
            router.handle_any_alert.call_args_list,
        )
        self.assertEqual([call(1), call(0.25)], sleep.call_args_list)
        ready.click.assert_called_once_with()

    def test_two_click_failures_return_ready_not_clickable(self):
        router = _router()

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(error=RuntimeError("first")),
                    _wait(error=RuntimeError("second")),
                ],
            ),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertEqual("READY_NOT_CLICKABLE", result)
        router.handle_any_alert.assert_called_once_with(timeout=1)
        sleep.assert_called_once_with(1)

    def test_nonduplicate_alert_without_overlay_returns_alert_handled(self):
        router = _router()
        alert = _alert("Informational alert")
        router.driver.switch_to.alert = alert

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(result=alert),
                    _wait(error=TimeoutException()),
                    _wait(error=TimeoutException()),
                ],
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertEqual("ALERT_HANDLED", result)
        alert.accept.assert_called_once_with()
        router.handle_duplicate_lni_popup.assert_not_called()

    def test_inventory_route_alert_returns_true_immediately(self):
        router = _router()
        alert = _alert(
            "Document cannot be processed for route - inventory route"
        )
        router.driver.switch_to.alert = alert

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(result=alert),
                ],
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertTrue(result)
        alert.accept.assert_called_once_with()

    def test_workflow_selection_alert_returns_true_immediately(self):
        router = _router()
        alert = _alert(
            "Document cannot be processed until workflow is selected"
        )
        router.driver.switch_to.alert = alert

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(result=alert),
                ],
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertTrue(result)

    def test_duplicate_alert_waits_for_clear_then_clicks_save(self):
        router = _router()
        alert = _alert("Duplicate Document")
        router.driver.switch_to.alert = alert
        clear_wait = _wait()

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(result=alert),
                    _wait(error=TimeoutException()),
                    clear_wait,
                ],
            ) as wait_type,
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertTrue(result)
        router.handle_duplicate_lni_popup.assert_called_once_with()
        clear_wait.until_not.assert_called_once()
        router.click_element.assert_called_once_with('//*[@id="add"]')
        self.assertEqual(call(router.driver, 5), wait_type.call_args_list[-1])

    def test_duplicate_clear_failure_returns_false_without_save(self):
        router = _router()
        alert = _alert("Duplicate document")
        router.driver.switch_to.alert = alert

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(result=alert),
                    _wait(error=TimeoutException()),
                    _wait(until_not_error=RuntimeError("overlay stuck")),
                ],
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertFalse(result)
        router.click_element.assert_not_called()

    def test_generic_overlay_clicks_ok_and_delegates_duplicate_overlay(self):
        router = _router()
        ok_button = Mock()

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(error=TimeoutException()),
                    _wait(result=Mock()),
                    _wait(result=ok_button),
                ],
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertTrue(result)
        self.assertEqual(
            [call(timeout=2), call()],
            router.handle_any_alert.call_args_list,
        )
        ok_button.click.assert_called_once_with()
        router.handle_duplicate_overlay.assert_called_once_with()

    def test_generic_overlay_without_ok_still_delegates_and_returns_true(self):
        router = _router()

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=[
                    _wait(result=Mock()),
                    _wait(error=TimeoutException()),
                    _wait(result=Mock()),
                    _wait(error=TimeoutException()),
                ],
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertTrue(result)
        router.handle_duplicate_overlay.assert_called_once_with()

    def test_postclick_inspection_error_returns_false_to_allow_save(self):
        router = _router()
        router.handle_any_alert.side_effect = RuntimeError(
            "inspection failed"
        )

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                return_value=_wait(result=Mock()),
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertFalse(result)

    def test_preclick_retry_alert_error_returns_ready_not_clickable(self):
        router = _router()
        router.handle_any_alert.side_effect = RuntimeError(
            "alert handling failed"
        )

        with (
            patch(
                _flow_symbol("WebDriverWait"),
                return_value=_wait(error=RuntimeError("not clickable")),
            ),
            patch(_flow_symbol("time.sleep")),
        ):
            result = CaseLawRouter.click_ready_checkbox_and_check_overlay(
                router
            )

        self.assertEqual("READY_NOT_CLICKABLE", result)

    @unittest.skipUnless(
        importlib.util.find_spec(
            "core.router_modes.ready_postclick_selenium"
        ),
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
            and node.name == "click_ready_checkbox_and_check_overlay"
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
            "core.router_modes.ready_postclick_selenium"
        ),
        "module boundary applies after extraction",
    )
    def test_extracted_module_excludes_routing_status_and_form_filling(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "ready_postclick_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn('//*[@id="readyToProcess"]', source)
        self.assertIn("router.handle_duplicate_lni_popup()", source)
        self.assertIn("router.handle_duplicate_overlay()", source)
        for excluded_term in (
            '//*[@id="route"]',
            "status_updates_buffer",
            "fill_irt_form",
            "select_route",
            "mspb_metadata",
            "itc_metadata",
        ):
            with self.subTest(excluded_term=excluded_term):
                self.assertNotIn(excluded_term, source)


if __name__ == "__main__":
    unittest.main()
