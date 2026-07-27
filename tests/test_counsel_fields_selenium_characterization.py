"""No-driver characterization tests for SMD/DAR counsel comment fields."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec("core.router_modes.counsel_fields_selenium"):
        return f"core.router_modes.counsel_fields_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router(existing_text=""):
    router = CaseLawRouter.__new__(CaseLawRouter)
    comments = Mock()
    comments.get_attribute.return_value = existing_text
    router.wait = Mock()
    router.wait.until.return_value = comments
    alert = Mock()
    alert.text = ""
    router.driver = Mock()
    router.driver.switch_to.alert = alert
    router.handle_duplicate_lni_popup = Mock()
    router.full_df = Mock()
    return router, comments, alert


class CounselFieldsSeleniumCharacterizationTests(unittest.TestCase):
    def test_matching_main_lnis_and_mapping_comments_preserve_merge_order(self):
        router, comments, _ = _router("Existing.")
        router.full_df.iterrows.return_value = [
            (0, {"FileName": "main_a.pdf", "LNI": "LNI-MAIN-A"}),
            (1, {"FileName": "other.pdf", "LNI": "LNI-OTHER"}),
            (2, {"FileName": "counsel_peer.pdf", "LNI": "LNI-COUNSEL"}),
            (3, {"FileName": "main_b.pdf", "LNI": "LNI-MAIN-B"}),
        ]
        row = {
            "FileName": "counsel_target.pdf",
            "Comments": "Mapping note",
        }

        def docket(_unused, file_name, dar_mode, wc_mode):
            if file_name in {
                "counsel_target.pdf",
                "main_a.pdf",
                "main_b.pdf",
                "counsel_peer.pdf",
            }:
                return "DOCKET-1"
            return "DOCKET-2"

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                side_effect=docket,
            ) as formatter,
            patch(
                _flow_symbol("is_counsel"),
                side_effect=lambda name, *_: name.startswith("counsel"),
            ),
        ):
            result = CaseLawRouter.handle_counsel_fields(
                router,
                row,
                dar_mode=True,
                wc_mode=False,
            )

        self.assertIsNone(result)
        self.assertEqual(
            call(None, "counsel_target.pdf", True, False),
            formatter.call_args_list[0],
        )
        comments.clear.assert_called_once_with()
        comments.send_keys.assert_called_once_with(
            "Existing; LNI-MAIN-A; LNI-MAIN-B; Mapping note"
        )

    def test_existing_main_lni_without_new_comment_returns_without_write(self):
        router, comments, _ = _router("Already linked LNI-MAIN-A.")
        router.full_df.iterrows.return_value = [
            (0, {"FileName": "main_a.pdf", "LNI": "LNI-MAIN-A"}),
        ]

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-1",
            ),
            patch(_flow_symbol("is_counsel"), return_value=False),
        ):
            result = CaseLawRouter.handle_counsel_fields(
                router,
                {"FileName": "counsel.pdf", "Comments": ""},
            )

        self.assertIsNone(result)
        comments.clear.assert_not_called()
        comments.send_keys.assert_not_called()

    def test_duplicate_alert_preserves_popup_handling_and_refill(self):
        router, comments, alert = _router("")
        router.full_df.iterrows.return_value = []
        alert.text = "Duplicate document detected"

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            return_value="DOCKET-1",
        ):
            result = CaseLawRouter.handle_counsel_fields(
                router,
                {"FileName": "counsel.pdf", "Comments": "Counsel note"},
            )

        self.assertIsNone(result)
        alert.accept.assert_called_once_with()
        router.handle_duplicate_lni_popup.assert_called_once_with()
        self.assertEqual(2, comments.clear.call_count)
        self.assertEqual(
            [call("Counsel note"), call("Counsel note")],
            comments.send_keys.call_args_list,
        )

    def test_comment_write_preserves_two_attempt_retry(self):
        router, comments, _ = _router("")
        router.full_df.iterrows.return_value = []
        comments.clear.side_effect = [RuntimeError("first"), None]

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-1",
            ),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.handle_counsel_fields(
                router,
                {"FileName": "counsel.pdf", "Comments": "Retry note"},
            )

        self.assertIsNone(result)
        self.assertEqual(2, comments.clear.call_count)
        comments.send_keys.assert_called_once_with("Retry note")
        sleep.assert_called_once_with(1)

    def test_comments_lookup_error_remains_swallowed(self):
        router, comments, _ = _router("")
        router.wait.until.side_effect = RuntimeError("missing comments")

        result = CaseLawRouter.handle_counsel_fields(
            router,
            {"FileName": "counsel.pdf", "Comments": "Note"},
        )

        self.assertIsNone(result)
        comments.clear.assert_not_called()

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.counsel_fields_selenium"),
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
            and node.name == "handle_counsel_fields"
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
        importlib.util.find_spec("core.router_modes.counsel_fields_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_contains_only_counsel_field_flow(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "counsel_fields_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("router.full_df.iterrows()", source)
        self.assertIn("handle_duplicate_lni_popup", source)
        self.assertIn("Comments", source)
        for unrelated_mode in ("MSPB", "ITC", "IRSPLR", "OHTAX0", "MNSUTB"):
            with self.subTest(unrelated_mode=unrelated_mode):
                self.assertNotIn(unrelated_mode, source)


if __name__ == "__main__":
    unittest.main()
