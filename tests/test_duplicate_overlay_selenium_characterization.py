"""No-driver characterization tests for duplicate-overlay UI handling."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import (
    TimeoutException,
    UnexpectedAlertPresentException,
)

from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec(
        "core.router_modes.duplicate_overlay_selenium"
    ):
        return f"core.router_modes.duplicate_overlay_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router._archive_duplicate_mode = False
    router.accept_pending_alerts = Mock(return_value=(False, False))
    router.click_duplicate_archive_radio = Mock()
    router.click_duplicate_process_radio = Mock()
    router.click_duplicate_continue_button = Mock()
    router.wait_for_duplicate_overlay_to_clear = Mock()
    router.log_duplicate_overlay_diagnostics = Mock()
    router.handle_duplicate_overlay = Mock(return_value=True)
    router.click_duplicate_dialog_element = Mock()
    router.find_duplicate_archive_option = Mock()
    router.find_duplicate_continue_button = Mock()
    router.element_is_inside_visible_dialog = Mock(return_value=False)
    return router


class DuplicateOverlaySeleniumCharacterizationTests(unittest.TestCase):
    def test_archive_policy_uses_state_only_when_argument_is_none(self):
        router = _router()

        self.assertFalse(
            CaseLawRouter.should_archive_duplicate(router, None)
        )
        router._archive_duplicate_mode = True
        self.assertTrue(
            CaseLawRouter.should_archive_duplicate(router, None)
        )
        self.assertFalse(
            CaseLawRouter.should_archive_duplicate(router, False)
        )
        self.assertTrue(
            CaseLawRouter.should_archive_duplicate(router, True)
        )

    def test_process_path_accepts_alerts_around_clicks_and_clears(self):
        router = _router()
        router.handle_duplicate_overlay = (
            CaseLawRouter.handle_duplicate_overlay.__get__(
                router,
                CaseLawRouter,
            )
        )

        result = router.handle_duplicate_overlay(
            archive_as_duplicate=False
        )

        self.assertTrue(result)
        router.click_duplicate_process_radio.assert_called_once_with(
            timeout=10
        )
        router.click_duplicate_archive_radio.assert_not_called()
        router.click_duplicate_continue_button.assert_called_once_with(
            timeout=10
        )
        router.wait_for_duplicate_overlay_to_clear.assert_called_once_with(
            timeout=15
        )
        self.assertEqual(
            [
                call(
                    initial_timeout=0.5,
                    followup_timeout=1,
                    max_alerts=5,
                ),
                call(
                    initial_timeout=0.5,
                    followup_timeout=1,
                    max_alerts=5,
                ),
                call(
                    initial_timeout=0.5,
                    followup_timeout=1,
                    max_alerts=5,
                ),
            ],
            router.accept_pending_alerts.call_args_list,
        )

    def test_archive_state_selects_archive_radio(self):
        router = _router()
        router._archive_duplicate_mode = True
        router.handle_duplicate_overlay = (
            CaseLawRouter.handle_duplicate_overlay.__get__(
                router,
                CaseLawRouter,
            )
        )

        result = router.handle_duplicate_overlay()

        self.assertTrue(result)
        router.click_duplicate_archive_radio.assert_called_once_with(
            timeout=10
        )
        router.click_duplicate_process_radio.assert_not_called()

    def test_unexpected_alert_accepts_and_retries_without_sleep(self):
        router = _router()
        router.click_duplicate_process_radio.side_effect = [
            UnexpectedAlertPresentException(),
            None,
        ]
        router.handle_duplicate_overlay = (
            CaseLawRouter.handle_duplicate_overlay.__get__(
                router,
                CaseLawRouter,
            )
        )

        with patch(_flow_symbol("time.sleep")) as sleep:
            result = router.handle_duplicate_overlay(False)

        self.assertTrue(result)
        self.assertEqual(2, router.click_duplicate_process_radio.call_count)
        self.assertEqual(5, router.accept_pending_alerts.call_count)
        sleep.assert_not_called()

    def test_three_generic_failures_sleep_twice_then_diagnose(self):
        router = _router()
        router.click_duplicate_process_radio.side_effect = RuntimeError(
            "overlay blocked"
        )
        router.handle_duplicate_overlay = (
            CaseLawRouter.handle_duplicate_overlay.__get__(
                router,
                CaseLawRouter,
            )
        )

        with patch(_flow_symbol("time.sleep")) as sleep:
            result = router.handle_duplicate_overlay(False)

        self.assertFalse(result)
        self.assertEqual(3, router.click_duplicate_process_radio.call_count)
        self.assertEqual([call(1), call(1)], sleep.call_args_list)
        router.log_duplicate_overlay_diagnostics.assert_called_once_with()

    def test_popup_without_alert_still_checks_overlay(self):
        router = _router()
        wait = Mock()
        wait.until.side_effect = TimeoutException()

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            result = CaseLawRouter.handle_duplicate_lni_popup(
                router,
                archive_as_duplicate=True,
            )

        self.assertIsNone(result)
        router.handle_duplicate_overlay.assert_called_once_with(
            archive_as_duplicate=True
        )

    def test_nonduplicate_alert_returns_before_overlay(self):
        router = _router()
        alert = Mock()
        alert.text = "Informational warning"
        router.driver.switch_to.alert = alert

        with patch(_flow_symbol("WebDriverWait"), return_value=Mock()):
            result = CaseLawRouter.handle_duplicate_lni_popup(router)

        self.assertIsNone(result)
        alert.accept.assert_called_once_with()
        router.handle_duplicate_overlay.assert_not_called()

    def test_duplicate_alert_accepts_then_handles_overlay(self):
        router = _router()
        alert = Mock()
        alert.text = "Duplicate Document"
        router.driver.switch_to.alert = alert

        with patch(_flow_symbol("WebDriverWait"), return_value=Mock()):
            CaseLawRouter.handle_duplicate_lni_popup(
                router,
                archive_as_duplicate=False,
            )

        alert.accept.assert_called_once_with()
        router.handle_duplicate_overlay.assert_called_once_with(
            archive_as_duplicate=False
        )

    def test_process_radio_click_uses_native_click_when_available(self):
        router = _router()
        radio = Mock()
        waits = [Mock(), Mock()]
        waits[0].until.return_value = radio

        with patch(
            _flow_symbol("WebDriverWait"),
            side_effect=waits,
        ) as wait_type:
            CaseLawRouter.click_duplicate_process_radio(
                router,
                timeout=7,
            )

        self.assertEqual(
            [call(router.driver, 7), call(router.driver, 2)],
            wait_type.call_args_list,
        )
        router.driver.execute_script.assert_called_once_with(
            "arguments[0].scrollIntoView({block: 'center'});",
            radio,
        )
        radio.click.assert_called_once_with()

    def test_process_radio_click_falls_back_to_javascript(self):
        router = _router()
        radio = Mock()
        waits = [Mock(), Mock()]
        waits[0].until.return_value = radio
        waits[1].until.side_effect = RuntimeError("not clickable")

        with patch(
            _flow_symbol("WebDriverWait"),
            side_effect=waits,
        ):
            CaseLawRouter.click_duplicate_process_radio(router)

        radio.click.assert_not_called()
        self.assertEqual(2, router.driver.execute_script.call_count)
        self.assertIn(
            "checked = true",
            router.driver.execute_script.call_args_list[1].args[0],
        )

    def test_archive_radio_javascript_false_delegates_element_click(self):
        router = _router()
        option = Mock()
        router.find_duplicate_archive_option.return_value = option
        router.driver.execute_script.return_value = False

        CaseLawRouter.click_duplicate_archive_radio(router, timeout=6)

        router.find_duplicate_archive_option.assert_called_once_with(
            timeout=6
        )
        router.click_duplicate_dialog_element.assert_called_once_with(option)

    def test_find_archive_option_returns_first_visible_enabled_match(self):
        router = _router()
        hidden = Mock()
        hidden.is_displayed.return_value = False
        enabled = Mock()
        enabled.is_displayed.return_value = True
        enabled.is_enabled.return_value = True
        router.driver.find_elements.side_effect = [
            [],
            [hidden, enabled],
        ]
        wait = Mock()
        wait.until.side_effect = lambda predicate: predicate(router.driver)

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            result = CaseLawRouter.find_duplicate_archive_option(
                router,
                timeout=8,
            )

        self.assertIs(enabled, result)

    def test_find_continue_button_falls_back_to_first_visible_button(self):
        router = _router()
        hidden = Mock()
        hidden.is_displayed.return_value = False
        visible = Mock()
        visible.is_displayed.return_value = True
        visible.is_enabled.return_value = True
        router.driver.find_elements.side_effect = [
            [],
            [],
            [],
            [],
            [hidden, visible],
        ]
        wait = Mock()
        wait.until.side_effect = lambda predicate: predicate(router.driver)

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            result = CaseLawRouter.find_duplicate_continue_button(router)

        self.assertIs(visible, result)

    def test_wait_for_clear_uses_absence_of_all_duplicate_ui(self):
        router = _router()
        router.driver.find_elements.return_value = []
        wait = Mock()
        wait.until.side_effect = lambda predicate: predicate(router.driver)

        with patch(_flow_symbol("WebDriverWait"), return_value=wait):
            result = CaseLawRouter.wait_for_duplicate_overlay_to_clear(
                router,
                timeout=11,
            )

        self.assertIsNone(result)
        self.assertEqual(4, router.driver.find_elements.call_count)

    @unittest.skipUnless(
        importlib.util.find_spec(
            "core.router_modes.duplicate_overlay_selenium"
        ),
        "structural boundary applies after extraction",
    )
    def test_router_methods_become_thin_compatibility_entry_points(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))
        method_names = (
            "should_archive_duplicate",
            "handle_duplicate_overlay",
            "handle_duplicate_lni_popup",
            "click_duplicate_process_radio",
            "click_duplicate_archive_radio",
            "find_duplicate_archive_option",
            "click_duplicate_continue_button",
            "find_duplicate_continue_button",
            "click_duplicate_dialog_element",
            "wait_for_duplicate_overlay_to_clear",
            "element_is_inside_visible_dialog",
            "log_duplicate_overlay_diagnostics",
        )

        for method_name in method_names:
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
            "core.router_modes.duplicate_overlay_selenium"
        ),
        "module boundary applies after extraction",
    )
    def test_extracted_module_excludes_routing_and_mode_metadata(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "duplicate_overlay_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("processDuplicate", source)
        self.assertIn("ARCHIVE AS DUPLICATE", source)
        self.assertIn("ui-widget-overlay", source)
        for excluded_term in (
            "status_updates_buffer",
            "handle_routing_and_save",
            '//*[@id="add"]',
            '//*[@id="route"]',
            "mspb_metadata",
            "itc_metadata",
        ):
            with self.subTest(excluded_term=excluded_term):
                self.assertNotIn(excluded_term, source)


if __name__ == "__main__":
    unittest.main()
