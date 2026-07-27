"""No-driver characterization tests for search-result navigation."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.smducar_router import CaseLawRouter, RouterSessionLostError


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.result_navigation_selenium"):
        return f"core.router_modes.result_navigation_selenium.{name}"
    if name == "ActionChains":
        return "selenium.webdriver.common.action_chains.ActionChains"
    return f"core.smducar_router.{name}"


class _Driver:
    def __init__(self, handle_snapshots):
        self._handle_snapshots = iter(handle_snapshots)
        self._last_handles = []
        self.current_window_handle = "main"
        self.switch_to = Mock()
        self.execute_script = Mock()

    @property
    def window_handles(self):
        try:
            self._last_handles = list(next(self._handle_snapshots))
        except StopIteration:
            pass
        return list(self._last_handles)


def _router(handle_snapshots=(("main",),)):
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = _Driver(handle_snapshots)
    router.search_wait = Mock()
    router.long_wait = Mock()
    router.wait = Mock()
    router.show_error = Mock()
    router._raise_if_invalid_session_error = Mock()
    router.search_lni = Mock(return_value=True)
    router.check_result_available = Mock(return_value=True)
    router.click_matching_result = Mock()
    return router


def _action(error=None):
    action = Mock()
    action.key_down.return_value = action
    action.click.return_value = action
    action.key_up.return_value = action
    action.context_click.return_value = action
    if error is not None:
        action.perform.side_effect = error
    return action


class ResultNavigationSeleniumCharacterizationTests(unittest.TestCase):
    def test_result_availability_uses_selector_and_returns_true(self):
        router = _router()
        condition = object()

        with patch(_flow_symbol("EC")) as conditions:
            conditions.presence_of_element_located.return_value = condition
            result = CaseLawRouter.check_result_available(router)

        self.assertTrue(result)
        locator = conditions.presence_of_element_located.call_args.args[0]
        self.assertEqual(
            "td.searchColumn.ChangeMouseCursorToHand",
            locator[1],
        )
        router.search_wait.until.assert_called_once_with(condition)

    def test_result_availability_failure_classifies_and_returns_false(self):
        router = _router()
        original = RuntimeError("result timeout")
        router.search_wait.until.side_effect = original

        result = CaseLawRouter.check_result_available(router)

        self.assertFalse(result)
        router._raise_if_invalid_session_error.assert_called_once_with(
            original,
            "checking LNI search results",
        )

    def test_result_availability_propagates_translated_session_loss(self):
        router = _router()
        router.search_wait.until.side_effect = RuntimeError(
            "invalid session id"
        )
        router._raise_if_invalid_session_error.side_effect = (
            RouterSessionLostError("lost checking results")
        )

        with self.assertRaisesRegex(
            RouterSessionLostError,
            "lost checking results",
        ):
            CaseLawRouter.check_result_available(router)

    def test_handle_lni_search_short_circuits_failed_search(self):
        router = _router()
        router.search_lni.return_value = False

        result = CaseLawRouter.handle_lni_search(router, "LNI-1")

        self.assertFalse(result)
        router.check_result_available.assert_not_called()
        router.click_matching_result.assert_not_called()

    def test_handle_lni_search_short_circuits_missing_result(self):
        router = _router()
        router.check_result_available.return_value = False

        result = CaseLawRouter.handle_lni_search(router, "LNI-2")

        self.assertFalse(result)
        router.check_result_available.assert_called_once_with()
        router.click_matching_result.assert_not_called()

    def test_handle_lni_search_clicks_result_and_returns_true(self):
        router = _router()

        result = CaseLawRouter.handle_lni_search(router, "LNI-3")

        self.assertTrue(result)
        router.search_lni.assert_called_once_with("LNI-3")
        router.check_result_available.assert_called_once_with()
        router.click_matching_result.assert_called_once_with()

    def test_ctrl_click_new_tab_records_both_handles(self):
        router = _router((("main",), ("main", "new-tab")))
        element = Mock()
        router.long_wait.until.return_value = element
        action = _action()

        with (
            patch(_flow_symbol("ActionChains"), return_value=action),
            patch(_flow_symbol("WebDriverWait"), return_value=Mock()),
        ):
            result = CaseLawRouter.click_matching_result(router)

        self.assertIsNone(result)
        router.driver.switch_to.window.assert_called_once_with("new-tab")
        self.assertEqual("new-tab", router._opened_tab)
        self.assertEqual("main", router._main_tab)
        router.driver.execute_script.assert_not_called()
        element.click.assert_not_called()

    def test_middle_click_is_used_after_ctrl_click_failure(self):
        router = _router((("main",), ("main", "middle-tab")))
        element = Mock()
        router.long_wait.until.return_value = element
        ctrl_action = _action(RuntimeError("ctrl failed"))

        with (
            patch(_flow_symbol("ActionChains"), return_value=ctrl_action),
            patch(_flow_symbol("WebDriverWait"), return_value=Mock()),
        ):
            CaseLawRouter.click_matching_result(router)

        router.driver.execute_script.assert_called_once()
        router.driver.switch_to.window.assert_called_once_with("middle-tab")
        self.assertEqual("middle-tab", router._opened_tab)
        self.assertEqual("main", router._main_tab)

    def test_context_menu_is_used_after_first_two_methods_fail(self):
        router = _router((("main",), ("main", "context-tab")))
        element = Mock()
        option = Mock()
        router.long_wait.until.return_value = element
        router.driver.execute_script.side_effect = RuntimeError("middle failed")
        ctrl_action = _action(RuntimeError("ctrl failed"))
        context_action = _action()
        waits = [Mock(), Mock()]
        waits[0].until.return_value = option

        with (
            patch(
                _flow_symbol("ActionChains"),
                side_effect=[ctrl_action, context_action],
            ),
            patch(
                _flow_symbol("WebDriverWait"),
                side_effect=waits,
            ) as wait_type,
        ):
            CaseLawRouter.click_matching_result(router)

        context_action.context_click.assert_called_once_with(element)
        option.click.assert_called_once_with()
        self.assertEqual(
            [call(router.driver, 3), call(router.driver, 5)],
            wait_type.call_args_list,
        )
        router.driver.switch_to.window.assert_called_once_with("context-tab")
        self.assertEqual("context-tab", router._opened_tab)

    def test_all_new_tab_methods_fall_back_to_direct_click(self):
        router = _router((("main",),))
        element = Mock()
        router.long_wait.until.return_value = element
        router.driver.execute_script.side_effect = RuntimeError("middle failed")
        failing_action = _action(RuntimeError("action failed"))

        with (
            patch(_flow_symbol("ActionChains"), return_value=failing_action),
            patch(
                _flow_symbol("WebDriverWait"),
                return_value=Mock(),
            ),
        ):
            CaseLawRouter.click_matching_result(router)

        element.click.assert_called_once_with()
        self.assertIsNone(router._opened_tab)
        self.assertEqual("main", router._main_tab)

    def test_outer_result_click_failure_reports_error_and_returns_none(self):
        router = _router()
        router.long_wait.until.side_effect = RuntimeError("result locked")

        result = CaseLawRouter.click_matching_result(router)

        self.assertIsNone(result)
        router.show_error.assert_called_once_with(
            "Failed to click search result"
        )
        self.assertFalse(hasattr(router, "_opened_tab"))
        router._raise_if_invalid_session_error.assert_not_called()

    def test_popup_switch_returns_first_handle(self):
        router = _router((("main", "popup"), ("main", "popup")))

        result = CaseLawRouter.switch_to_popup_window(router)

        self.assertEqual("main", result)
        router.driver.switch_to.window.assert_called_once_with("popup")

    def test_popup_switch_failure_reports_error_and_returns_none(self):
        router = _router()
        router.wait.until.side_effect = RuntimeError("no popup")

        result = CaseLawRouter.switch_to_popup_window(router)

        self.assertIsNone(result)
        router.show_error.assert_called_once_with(
            "Failed to switch to popup window"
        )

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.result_navigation_selenium"),
        "structural boundary applies after extraction",
    )
    def test_router_methods_become_thin_compatibility_entry_points(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))

        for method_name in (
            "check_result_available",
            "handle_lni_search",
            "click_matching_result",
            "switch_to_popup_window",
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
        importlib.util.find_spec("core.router_modes.result_navigation_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_excludes_form_and_duplicate_processing(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "result_navigation_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("td.searchColumn.ChangeMouseCursorToHand", source)
        self.assertIn("router._opened_tab", source)
        self.assertIn("router._main_tab", source)
        for excluded_term in (
            '//*[@id="modify"]',
            "open_and_process_form",
            "fill_irt_form",
            "handle_duplicate",
            "status_updates_buffer",
        ):
            with self.subTest(excluded_term=excluded_term):
                self.assertNotIn(excluded_term, source)


if __name__ == "__main__":
    unittest.main()
