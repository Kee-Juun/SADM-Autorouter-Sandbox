"""No-driver characterization tests for the LNI search retry loop."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.smducar_router import CaseLawRouter, RouterSessionLostError


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.lni_search_selenium"):
        return f"core.router_modes.lni_search_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.search_wait = Mock()
    router.wait = Mock()
    router.check_session_validity = Mock(return_value=True)
    router.check_result_available = Mock(return_value=True)
    router.refresh_search_inventory_for_retry = Mock(return_value=True)
    router._is_invalid_session_error = Mock(return_value=False)
    return router


class LniSearchSeleniumCharacterizationTests(unittest.TestCase):
    def test_first_attempt_enters_value_clicks_search_and_returns_true(self):
        router = _router()
        field = Mock()
        button = Mock()
        router.search_wait.until.return_value = field
        router.wait.until.return_value = button

        with (
            patch(_flow_symbol("time.sleep")) as sleep,
            patch(_flow_symbol("EC")) as conditions,
        ):
            field_condition = object()
            button_condition = object()
            conditions.presence_of_element_located.return_value = (
                field_condition
            )
            conditions.element_to_be_clickable.return_value = button_condition
            result = CaseLawRouter.search_lni(router, "LNI-123")

        self.assertTrue(result)
        field.clear.assert_called_once_with()
        field.send_keys.assert_called_once_with("LNI-123")
        button.click.assert_called_once_with()
        self.assertEqual([call(0.5), call(0.5)], sleep.call_args_list)
        router.search_wait.until.assert_called_once_with(field_condition)
        router.wait.until.assert_called_once_with(button_condition)
        field_locator = (
            conditions.presence_of_element_located.call_args.args[0]
        )
        button_locator = conditions.element_to_be_clickable.call_args.args[0]
        self.assertEqual('//*[@id="documentLNISearch"]', field_locator[1])
        self.assertEqual('//*[@id="search"]', button_locator[1])
        router.refresh_search_inventory_for_retry.assert_not_called()

    def test_no_result_refreshes_then_second_attempt_can_succeed(self):
        router = _router()
        fields = [Mock(), Mock()]
        buttons = [Mock(), Mock()]
        router.search_wait.until.side_effect = fields
        router.wait.until.side_effect = buttons
        router.check_result_available.side_effect = [False, True]

        with patch(_flow_symbol("time.sleep")) as sleep:
            result = CaseLawRouter.search_lni(router, "LNI-RETRY")

        self.assertTrue(result)
        router.refresh_search_inventory_for_retry.assert_called_once_with(
            reason="LNI search retry after no result appeared"
        )
        self.assertEqual(
            [call(0.5), call(0.5), call(2), call(0.5), call(0.5)],
            sleep.call_args_list,
        )
        self.assertEqual(2, router.check_session_validity.call_count)

    def test_failed_refresh_confirmation_does_not_stop_retry(self):
        router = _router()
        router.search_wait.until.side_effect = [Mock(), Mock()]
        router.wait.until.side_effect = [Mock(), Mock()]
        router.check_result_available.side_effect = [False, True]
        router.refresh_search_inventory_for_retry.return_value = False

        with patch(_flow_symbol("time.sleep")):
            result = CaseLawRouter.search_lni(router, "LNI-RECOVER")

        self.assertTrue(result)
        router.refresh_search_inventory_for_retry.assert_called_once()

    def test_third_no_result_does_not_run_another_recovery(self):
        router = _router()
        router.search_wait.until.side_effect = [Mock(), Mock(), Mock()]
        router.wait.until.side_effect = [Mock(), Mock(), Mock()]
        router.check_result_available.return_value = False

        with patch(_flow_symbol("time.sleep")) as sleep:
            result = CaseLawRouter.search_lni(router, "LNI-MISSING")

        self.assertFalse(result)
        self.assertEqual(
            [
                call(
                    reason="LNI search retry after no result appeared"
                ),
                call(
                    reason="LNI search retry after no result appeared"
                ),
            ],
            router.refresh_search_inventory_for_retry.call_args_list,
        )
        self.assertEqual(2, sleep.call_args_list.count(call(2)))
        self.assertEqual(6, sleep.call_args_list.count(call(0.5)))

    def test_ordinary_search_exception_recovers_before_next_attempt(self):
        router = _router()
        original = RuntimeError("field unavailable")
        field = Mock()
        router.search_wait.until.side_effect = [original, field]
        router.wait.until.return_value = Mock()

        with patch(_flow_symbol("time.sleep")) as sleep:
            result = CaseLawRouter.search_lni(router, "LNI-ERROR")

        self.assertTrue(result)
        router._is_invalid_session_error.assert_called_once_with(original)
        router.refresh_search_inventory_for_retry.assert_called_once_with(
            reason="LNI search retry after field unavailable"
        )
        self.assertEqual(
            [call(2), call(0.5), call(0.5)],
            sleep.call_args_list,
        )

    def test_empty_exception_message_uses_search_exception_reason(self):
        router = _router()
        router.search_wait.until.side_effect = [RuntimeError(), Mock()]
        router.wait.until.return_value = Mock()

        with patch(_flow_symbol("time.sleep")):
            result = CaseLawRouter.search_lni(router, "LNI-EMPTY")

        self.assertTrue(result)
        router.refresh_search_inventory_for_retry.assert_called_once_with(
            reason="LNI search retry after search exception"
        )

    def test_classified_session_error_preserves_translation_and_cause(self):
        router = _router()
        original = RuntimeError("invalid session id")
        router.search_wait.until.side_effect = original
        router._is_invalid_session_error.return_value = True

        with self.assertRaisesRegex(
            RouterSessionLostError,
            "lost during LNI search for LNI-LOST",
        ) as raised:
            CaseLawRouter.search_lni(router, "LNI-LOST")

        self.assertIs(original, raised.exception.__cause__)
        router.refresh_search_inventory_for_retry.assert_not_called()

    def test_invalid_precheck_retains_legacy_retry_and_false_result(self):
        router = _router()
        router.check_session_validity.return_value = False

        with patch(_flow_symbol("time.sleep")) as sleep:
            result = CaseLawRouter.search_lni(router, "LNI-PRECHECK")

        self.assertFalse(result)
        self.assertEqual(3, router.check_session_validity.call_count)
        self.assertEqual(
            2,
            router.refresh_search_inventory_for_retry.call_count,
        )
        self.assertEqual([call(2), call(2)], sleep.call_args_list)
        router.search_wait.until.assert_not_called()

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.lni_search_selenium"),
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
            if isinstance(node, ast.FunctionDef) and node.name == "search_lni"
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
        importlib.util.find_spec("core.router_modes.lni_search_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_excludes_result_selection_and_form_opening(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "lni_search_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn('//*[@id="documentLNISearch"]', source)
        self.assertIn('//*[@id="search"]', source)
        self.assertIn("router.check_result_available()", source)
        for excluded_term in (
            "td.searchColumn",
            "click_matching_result",
            "open_and_process_form",
            "attempt_open_modify",
            "handle_duplicate",
        ):
            with self.subTest(excluded_term=excluded_term):
                self.assertNotIn(excluded_term, source)


if __name__ == "__main__":
    unittest.main()
