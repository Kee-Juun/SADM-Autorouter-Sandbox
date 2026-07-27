"""No-driver characterization tests for related counsel LNI attachment."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import TimeoutException

from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.related_lni_selenium"):
        return f"core.router_modes.related_lni_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.long_wait = Mock()
    router.wait = Mock()
    router.driver = Mock()
    router.clear_and_fill_input = Mock(return_value=True)
    router.show_error = Mock()
    return router


class RelatedLNISeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_no_related_lnis_preserves_status_and_early_failure(self):
        router = _router()
        row = {
            "FileName": "main.pdf",
            "RecycledCounselLNI": "RECYCLED-1",
        }
        full_df = object()

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-1",
            ) as formatter,
            patch(
                _flow_symbol("get_related_counsel_lnis"),
                return_value=[],
            ) as related,
        ):
            result = CaseLawRouter.handle_related_ln_is(
                router,
                row,
                full_df,
                row_index=90,
                file_path="mapping.xlsx",
                dar_mode=True,
                wc_mode=False,
            )

        self.assertFalse(result)
        self.assertEqual("NO COUNSEL ATTACHED", status_updates_buffer[90])
        formatter.assert_called_once_with(None, "main.pdf", True, False)
        related.assert_called_once_with(
            "DOCKET-1",
            full_df,
            recycled_lni="RECYCLED-1",
            dar_mode=True,
            wc_mode=False,
        )
        router.long_wait.until.assert_not_called()

    def test_existing_related_lni_preserves_success_without_add(self):
        router = _router()
        initial_box = Mock()
        initial_box.text = "LNI-EXISTING\n"
        final_box = Mock()
        final_box.text = "LNI-EXISTING\n"
        router.long_wait.until.side_effect = [initial_box, final_box]

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-2",
            ),
            patch(
                _flow_symbol("get_related_counsel_lnis"),
                return_value=["LNI-EXISTING"],
            ),
        ):
            result = CaseLawRouter.handle_related_ln_is(
                router,
                {"FileName": "main.pdf"},
                object(),
                row_index=91,
            )

        self.assertTrue(result)
        router.clear_and_fill_input.assert_not_called()
        router.wait.until.assert_not_called()

    def test_new_lni_preserves_input_add_wait_and_final_verification(self):
        router = _router()
        initial_box = Mock()
        initial_box.text = ""
        final_box = Mock()
        final_box.text = "LNI-NEW\n"
        router.long_wait.until.side_effect = [initial_box, True, final_box]
        add_button = Mock()
        router.wait.until.return_value = add_button

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-3",
            ),
            patch(
                _flow_symbol("get_related_counsel_lnis"),
                return_value=["LNI-NEW"],
            ),
        ):
            result = CaseLawRouter.handle_related_ln_is(
                router,
                {"FileName": "main.pdf"},
                object(),
                row_index=92,
            )

        self.assertTrue(result)
        router.clear_and_fill_input.assert_called_once_with(
            '//*[@id="relateLNIs"]',
            "LNI-NEW",
        )
        add_button.click.assert_called_once_with()
        self.assertEqual(3, router.long_wait.until.call_count)
        self.assertNotIn(92, status_updates_buffer)

    def test_locked_related_input_preserves_status_and_failure(self):
        router = _router()
        initial_box = Mock()
        initial_box.text = ""
        router.long_wait.until.return_value = initial_box
        router.clear_and_fill_input.return_value = False

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-4",
            ),
            patch(
                _flow_symbol("get_related_counsel_lnis"),
                return_value=["LNI-LOCKED"],
            ),
        ):
            result = CaseLawRouter.handle_related_ln_is(
                router,
                {"FileName": "main.pdf"},
                object(),
                row_index=93,
            )

        self.assertFalse(result)
        self.assertEqual(
            "RELATED LNI FIELD LOCKED",
            status_updates_buffer[93],
        )
        router.wait.until.assert_not_called()

    def test_attachment_timeout_preserves_notification_and_status(self):
        router = _router()
        initial_box = Mock()
        initial_box.text = ""
        router.long_wait.until.return_value = initial_box
        router.wait.until.side_effect = TimeoutException("timed out")

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-5",
            ),
            patch(
                _flow_symbol("get_related_counsel_lnis"),
                return_value=["LNI-TIMEOUT"],
            ),
        ):
            result = CaseLawRouter.handle_related_ln_is(
                router,
                {"FileName": "main.pdf"},
                object(),
                row_index=94,
            )

        self.assertFalse(result)
        self.assertEqual("RELATED LNI TIMEOUT", status_updates_buffer[94])
        router.show_error.assert_called_once()
        message = router.show_error.call_args.args[0]
        self.assertIn("LNI-TIMEOUT", message)
        self.assertIn("DOCKET-5", message)
        self.assertIn("5 minutes", message)

    def test_invalid_and_unverified_lnis_preserve_no_counsel_status(self):
        router = _router()
        initial_box = Mock()
        initial_box.text = ""
        final_box = Mock()
        final_box.text = ""
        router.long_wait.until.side_effect = [initial_box, final_box]

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-6",
            ),
            patch(
                _flow_symbol("get_related_counsel_lnis"),
                return_value=["", "nan"],
            ),
        ):
            result = CaseLawRouter.handle_related_ln_is(
                router,
                {"FileName": "main.pdf"},
                object(),
                row_index=95,
            )

        self.assertFalse(result)
        self.assertEqual("NO COUNSEL ATTACHED", status_updates_buffer[95])
        router.clear_and_fill_input.assert_not_called()

    def test_outer_error_preserves_related_lni_error_status(self):
        router = _router()

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            side_effect=RuntimeError("bad docket"),
        ):
            result = CaseLawRouter.handle_related_ln_is(
                router,
                {"FileName": "main.pdf"},
                object(),
                row_index=96,
            )

        self.assertFalse(result)
        self.assertEqual("RELATED LNI ERROR", status_updates_buffer[96])

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.related_lni_selenium"),
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
            and node.name == "handle_related_ln_is"
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
        importlib.util.find_spec("core.router_modes.related_lni_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_remains_lni_only_without_filesystem_work(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "related_lni_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("get_related_counsel_lnis", source)
        self.assertIn("AddRelated", source)
        self.assertIn("RELATED LNI TIMEOUT", source)
        self.assertNotIn("pathlib", source)
        self.assertNotIn("os.path", source)
        for unrelated_mode in ("MSPB", "ITC", "IRSPLR", "OHTAX0", "MNSUTB"):
            with self.subTest(unrelated_mode=unrelated_mode):
                self.assertNotIn(unrelated_mode, source)


if __name__ == "__main__":
    unittest.main()
