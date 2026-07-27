"""No-driver characterization tests for router tab cleanup and focus."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call

from core.smducar_router import CaseLawRouter, RouterSessionLostError


class TabLifecycleSeleniumCharacterizationTests(unittest.TestCase):
    def _router(self, handles):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.driver = Mock()
        router.driver.window_handles = list(handles)
        router._raise_if_invalid_session_error = Mock()
        router._opened_tab = "opened"
        router._main_tab = "main"
        return router

    def test_recovery_cleanup_closes_all_extras_and_focuses_tracked_main(self):
        router = self._router(["extra-1", "main", "extra-2"])

        result = CaseLawRouter._close_extra_tabs_and_focus_main(router)

        self.assertTrue(result)
        self.assertEqual(
            [
                call("extra-1"),
                call("extra-2"),
                call("main"),
            ],
            router.driver.switch_to.window.call_args_list,
        )
        self.assertEqual(2, router.driver.close.call_count)
        self.assertIsNone(router._opened_tab)
        self.assertEqual("main", router._main_tab)

    def test_recovery_cleanup_uses_first_handle_when_tracked_main_is_stale(self):
        router = self._router(["first", "second"])
        router._main_tab = "stale"

        result = CaseLawRouter._close_extra_tabs_and_focus_main(router)

        self.assertTrue(result)
        self.assertEqual(
            [call("second"), call("first")],
            router.driver.switch_to.window.call_args_list,
        )
        router.driver.close.assert_called_once_with()
        self.assertEqual("first", router._main_tab)

    def test_recovery_cleanup_without_windows_preserves_session_lost_error(self):
        router = self._router([])

        with self.assertRaisesRegex(
            RouterSessionLostError,
            "no open windows",
        ):
            CaseLawRouter._close_extra_tabs_and_focus_main(router)

        self.assertEqual("opened", router._opened_tab)
        self.assertEqual("main", router._main_tab)

    def test_recovery_cleanup_nonfatal_close_error_still_focuses_main(self):
        router = self._router(["main", "extra"])
        router.driver.close.side_effect = RuntimeError("close failed")

        result = CaseLawRouter._close_extra_tabs_and_focus_main(router)

        self.assertTrue(result)
        router._raise_if_invalid_session_error.assert_called_once()
        self.assertEqual(
            [call("extra"), call("main")],
            router.driver.switch_to.window.call_args_list,
        )
        self.assertIsNone(router._opened_tab)
        self.assertEqual("main", router._main_tab)

    def test_local_cleanup_closes_opened_tab_then_focuses_main(self):
        router = self._router(["main", "opened"])

        result = CaseLawRouter._cleanup_tabs(router, "opened", "main")

        self.assertIsNone(result)
        self.assertEqual(
            [call("opened"), call("main")],
            router.driver.switch_to.window.call_args_list,
        )
        router.driver.close.assert_called_once_with()
        self.assertIsNone(router._opened_tab)
        self.assertIsNone(router._main_tab)

    def test_local_cleanup_falls_back_to_first_available_handle(self):
        router = self._router(["fallback", "other"])

        CaseLawRouter._cleanup_tabs(router, None, "missing")

        router.driver.close.assert_not_called()
        router.driver.switch_to.window.assert_called_once_with("fallback")
        self.assertIsNone(router._opened_tab)
        self.assertIsNone(router._main_tab)

    def test_local_cleanup_swallows_driver_error_and_resets_tracking(self):
        router = self._router(["main", "opened"])
        router.driver.switch_to.window.side_effect = RuntimeError(
            "switch failed"
        )

        result = CaseLawRouter._cleanup_tabs(router, "opened", "main")

        self.assertIsNone(result)
        router.driver.close.assert_not_called()
        self.assertIsNone(router._opened_tab)
        self.assertIsNone(router._main_tab)

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.tab_lifecycle_selenium"),
        "structural boundary applies after extraction",
    )
    def test_router_methods_become_thin_compatibility_entry_points(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))

        for method_name in (
            "_close_extra_tabs_and_focus_main",
            "_cleanup_tabs",
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
        importlib.util.find_spec("core.router_modes.tab_lifecycle_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_contains_only_tab_lifecycle_policy(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "tab_lifecycle_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("window_handles", source)
        self.assertIn("switch_to.window", source)
        self.assertIn("router.driver.close()", source)
        self.assertNotIn("documentLNISearch", source)
        self.assertNotIn("alert_is_present", source)
        self.assertNotIn("handle_duplicate_overlay", source)
        self.assertNotIn("status_updates_buffer", source)


if __name__ == "__main__":
    unittest.main()
