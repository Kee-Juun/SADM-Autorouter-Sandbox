"""Characterization tests for form-opening and Modify retry orchestration."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.driver.current_window_handle = "driver-main"
    router._main_tab = "tracked-main"
    router._opened_tab = "tracked-form"
    router.attempt_open_modify = Mock(return_value=True)
    router.fill_irt_form = Mock(return_value="DONE")
    router.submit_irt_form = Mock()
    router._cleanup_tabs = Mock()
    router.refresh_search_inventory_for_retry = Mock(return_value=True)
    router.handle_lni_search = Mock(return_value=True)
    return router


def _call(router, **overrides):
    arguments = {
        "row": {"LNI": "  LNI-123  "},
        "full_df": object(),
        "row_index": 40,
        "file_path": "mapping.xlsx",
        "retry_count": 0,
        "dar_mode": True,
        "wc_mode": True,
        "mspb_mode": True,
        "mspb_metadata": "mspb",
        "itc_metadata": "itc",
        "irsplr_metadata": "irsplr",
        "ohtax0_metadata": "ohtax0",
        "mnsutb_metadata": "mnsutb",
    }
    arguments.update(overrides)
    return CaseLawRouter.open_and_process_form(router, **arguments)


class FormOpeningSeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_done_status_submits_records_and_cleans_tracked_tabs(self):
        router = _router()

        result = _call(router)

        self.assertEqual("DONE", result)
        router.attempt_open_modify.assert_called_once_with(row_index=40)
        router.fill_irt_form.assert_called_once()
        fill_call = router.fill_irt_form.call_args
        self.assertEqual(
            (
                {"LNI": "  LNI-123  "},
                fill_call.args[1],
                40,
                "mapping.xlsx",
            ),
            fill_call.args,
        )
        self.assertEqual(
            {
                "skip_ready_check": True,
                "dar_mode": True,
                "wc_mode": True,
                "mspb_mode": True,
                "mspb_metadata": "mspb",
                "itc_metadata": "itc",
                "irsplr_metadata": "irsplr",
                "ohtax0_metadata": "ohtax0",
                "mnsutb_metadata": "mnsutb",
            },
            fill_call.kwargs,
        )
        router.submit_irt_form.assert_called_once_with("mapping.xlsx", 40)
        self.assertEqual("DONE", status_updates_buffer[40])
        router._cleanup_tabs.assert_called_once_with(
            "tracked-form",
            "tracked-main",
        )

    def test_non_done_status_skips_submission_but_still_cleans_tabs(self):
        router = _router()
        router.fill_irt_form.return_value = "ALREADY PROCESSED"

        result = _call(router)

        self.assertEqual("ALREADY PROCESSED", result)
        router.submit_irt_form.assert_not_called()
        self.assertNotIn(40, status_updates_buffer)
        router._cleanup_tabs.assert_called_once_with(
            "tracked-form",
            "tracked-main",
        )

    def test_missing_tracking_uses_driver_main_and_none_opened_tab(self):
        router = _router()
        del router._main_tab
        del router._opened_tab

        _call(router)

        router._cleanup_tabs.assert_called_once_with(
            None,
            "driver-main",
        )

    def test_failed_modify_and_failed_refresh_write_exact_status(self):
        router = _router()
        router.attempt_open_modify.return_value = False
        router.refresh_search_inventory_for_retry.return_value = False

        result = _call(router)

        self.assertEqual("ERROR: MODIFY REFRESH RETRY FAILED", result)
        self.assertEqual(result, status_updates_buffer[40])
        router._cleanup_tabs.assert_called_once_with(
            "tracked-form",
            "tracked-main",
        )
        router.refresh_search_inventory_for_retry.assert_called_once_with(
            reason="Modify button not found for LNI LNI-123"
        )
        router.handle_lni_search.assert_not_called()

    def test_failed_research_writes_exact_status(self):
        router = _router()
        router.attempt_open_modify.return_value = False
        router.handle_lni_search.return_value = False

        result = _call(router, retry_count=1)

        self.assertEqual("ERROR: LNI RE-SEARCH FAILED", result)
        self.assertEqual(result, status_updates_buffer[40])
        router.refresh_search_inventory_for_retry.assert_called_once()
        router.handle_lni_search.assert_called_once_with("LNI-123")

    def test_successful_research_recurses_with_all_arguments(self):
        router = _router()
        router.attempt_open_modify.return_value = False
        router.open_and_process_form = Mock(return_value="RECURSED")
        full_df = object()
        row = {"LNI": " LNI-RECURSE "}

        result = _call(
            router,
            row=row,
            full_df=full_df,
            retry_count=0,
        )

        self.assertEqual("RECURSED", result)
        router.open_and_process_form.assert_called_once_with(
            row,
            full_df,
            40,
            "mapping.xlsx",
            retry_count=1,
            dar_mode=True,
            wc_mode=True,
            mspb_mode=True,
            mspb_metadata="mspb",
            itc_metadata="itc",
            irsplr_metadata="irsplr",
            ohtax0_metadata="ohtax0",
            mnsutb_metadata="mnsutb",
        )

    def test_third_failed_modify_stops_without_refreshing(self):
        router = _router()
        router.attempt_open_modify.return_value = False

        result = _call(router, retry_count=2)

        self.assertEqual(
            "ERROR: MODIFY BUTTON NOT FOUND AFTER 3 ATTEMPTS",
            result,
        )
        self.assertEqual(result, status_updates_buffer[40])
        router.refresh_search_inventory_for_retry.assert_not_called()
        router.handle_lni_search.assert_not_called()
        router._cleanup_tabs.assert_called_once()

    def test_fill_exception_propagates_without_cleanup(self):
        router = _router()
        router.fill_irt_form.side_effect = RuntimeError("fill failed")

        with self.assertRaisesRegex(RuntimeError, "fill failed"):
            _call(router)

        router.submit_irt_form.assert_not_called()
        router._cleanup_tabs.assert_not_called()

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.form_opening_selenium"),
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
            and node.name == "open_and_process_form"
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
        importlib.util.find_spec("core.router_modes.form_opening_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_is_selector_free_orchestration(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "form_opening_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("router.attempt_open_modify(", source)
        self.assertIn("router.fill_irt_form(", source)
        self.assertIn("router.handle_lni_search(", source)
        for excluded_term in (
            "from selenium",
            "WebDriverWait",
            "By.XPATH",
            "handle_duplicate",
            "td.searchColumn",
        ):
            with self.subTest(excluded_term=excluded_term):
                self.assertNotIn(excluded_term, source)


if __name__ == "__main__":
    unittest.main()
