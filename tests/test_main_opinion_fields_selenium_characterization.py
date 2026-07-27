"""No-driver characterization tests for SMD/DAR main-opinion fields."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from selenium.common.exceptions import TimeoutException

from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _flow_symbol(name):
    if importlib.util.find_spec(
        "core.router_modes.main_opinion_fields_selenium"
    ):
        return f"core.router_modes.main_opinion_fields_selenium.{name}"
    return f"core.smducar_router.{name}"


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.wait = Mock()
    router.driver = Mock()
    router.driver.window_handles = ["main"]
    router.clear_and_fill_input = Mock()
    router.click_element = Mock()
    router.handle_duplicate_lni_popup = Mock()
    router.handle_related_ln_is = Mock(return_value=True)
    return router


class MainOpinionFieldsSeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_success_preserves_source_related_and_comment_sequence(self):
        router = _router()
        events = []
        case_field = Mock()
        case_field.get_attribute.return_value = ""
        source_dropdown = Mock()
        source_dropdown.click.side_effect = lambda: events.append("source-click")
        comments = Mock()
        comments.is_enabled.return_value = True
        comments.get_attribute.return_value = "Existing."
        route = Mock()
        route.is_enabled.return_value = True
        router.wait.until.side_effect = [
            case_field,
            source_dropdown,
            comments,
            route,
            comments,
        ]
        router.click_element.side_effect = lambda *_args, **_kwargs: events.append(
            "related-click"
        )
        router.handle_related_ln_is.side_effect = (
            lambda *_args, **_kwargs: events.append("related-delegate") or True
        )
        wait = Mock()
        wait.until.side_effect = TimeoutException()
        dropdown = Mock()
        row = {
            "FileName": "main.pdf",
            "SourceDetail": "raw source",
            "Comments": "Mapping note",
        }
        full_df = object()

        with (
            patch(
                _flow_symbol("resolve_source_detail"),
                return_value="Resolved Source",
            ),
            patch(_flow_symbol("WebDriverWait"), return_value=wait),
            patch(_flow_symbol("Select"), return_value=dropdown),
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-1",
            ) as formatter,
        ):
            result = CaseLawRouter.handle_main_opinion_fields(
                router,
                row,
                full_df,
                80,
                "mapping.xlsx",
                dar_mode=True,
                wc_mode=False,
            )

        self.assertIsNone(result)
        router.clear_and_fill_input.assert_called_once_with(
            '//*[@id="caseName"]',
            "RE",
        )
        dropdown.select_by_visible_text.assert_called_once_with(
            "Resolved Source"
        )
        router.click_element.assert_called_once_with(
            '//*[@id="related"]',
            wait_time=0,
        )
        formatter.assert_called_once_with(None, "main.pdf", True, False)
        router.handle_related_ln_is.assert_called_once_with(
            row,
            full_df,
            row_index=80,
            file_path="mapping.xlsx",
            dar_mode=True,
            wc_mode=False,
        )
        self.assertEqual(
            ["source-click", "related-click", "related-delegate"],
            events,
        )
        comments.clear.assert_called_once_with()
        comments.send_keys.assert_called_once_with(
            "Existing; Mapping note"
        )

    def test_missing_related_preserves_existing_status_and_cleanup(self):
        router = _router()
        case_field = Mock()
        case_field.get_attribute.return_value = "RE"
        router.wait.until.return_value = case_field
        router.handle_related_ln_is.return_value = False
        status_updates_buffer[81] = "Attachment mismatch"

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            return_value="DOCKET-2",
        ):
            result = CaseLawRouter.handle_main_opinion_fields(
                router,
                {
                    "FileName": "main.pdf",
                    "SourceDetail": "",
                    "Comments": "",
                },
                object(),
                81,
                "mapping.xlsx",
            )

        self.assertEqual("Attachment mismatch", result)
        self.assertEqual("Attachment mismatch", status_updates_buffer[81])
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    def test_missing_related_without_status_preserves_default_status(self):
        router = _router()
        case_field = Mock()
        case_field.get_attribute.return_value = "RE"
        router.wait.until.return_value = case_field
        router.handle_related_ln_is.return_value = False

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            return_value="DOCKET-3",
        ):
            result = CaseLawRouter.handle_main_opinion_fields(
                router,
                {
                    "FileName": "main.pdf",
                    "SourceDetail": "",
                    "Comments": "",
                },
                object(),
                82,
                "mapping.xlsx",
            )

        self.assertEqual("Missing Counsel Information", result)
        self.assertEqual(
            "Missing Counsel Information",
            status_updates_buffer[82],
        )

    def test_noninteractable_comments_and_route_preserve_status(self):
        router = _router()
        case_field = Mock()
        case_field.get_attribute.return_value = "RE"
        comments = Mock()
        comments.is_enabled.return_value = False
        route = Mock()
        route.is_enabled.return_value = False
        router.wait.until.side_effect = [case_field, comments, route]

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            return_value="DOCKET-4",
        ):
            result = CaseLawRouter.handle_main_opinion_fields(
                router,
                {
                    "FileName": "main.pdf",
                    "SourceDetail": "",
                    "Comments": "",
                },
                object(),
                83,
                "mapping.xlsx",
            )

        self.assertEqual("Non-interactable IRT Form", result)
        self.assertEqual(
            "Non-interactable IRT Form",
            status_updates_buffer[83],
        )
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    def test_duplicate_alert_after_source_click_preserves_popup_handling(self):
        router = _router()
        case_field = Mock()
        case_field.get_attribute.return_value = "RE"
        source_dropdown = Mock()
        comments = Mock()
        comments.is_enabled.return_value = True
        route = Mock()
        route.is_enabled.return_value = True
        router.wait.until.side_effect = [
            case_field,
            source_dropdown,
            comments,
            route,
        ]
        alert = Mock()
        alert.text = "Duplicate document detected"
        router.driver.switch_to.alert = alert
        wait = Mock()
        wait.until.return_value = alert
        dropdown = Mock()

        with (
            patch(
                _flow_symbol("resolve_source_detail"),
                return_value="Resolved Source",
            ),
            patch(_flow_symbol("WebDriverWait"), return_value=wait),
            patch(_flow_symbol("Select"), return_value=dropdown),
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-5",
            ),
        ):
            result = CaseLawRouter.handle_main_opinion_fields(
                router,
                {
                    "FileName": "main.pdf",
                    "SourceDetail": "raw",
                    "Comments": "",
                },
                object(),
                84,
                "mapping.xlsx",
            )

        self.assertIsNone(result)
        alert.accept.assert_called_once_with()
        router.handle_duplicate_lni_popup.assert_called_once_with()
        dropdown.select_by_visible_text.assert_called_once_with(
            "Resolved Source"
        )

    def test_comment_write_preserves_two_attempt_retry(self):
        router = _router()
        case_field = Mock()
        case_field.get_attribute.return_value = "RE"
        comments = Mock()
        comments.is_enabled.return_value = True
        comments.get_attribute.return_value = ""
        comments.clear.side_effect = [RuntimeError("first"), None]
        route = Mock()
        route.is_enabled.return_value = True
        router.wait.until.side_effect = [
            case_field,
            comments,
            route,
            comments,
        ]

        with (
            patch.object(
                CaseLawRouter,
                "format_docket_number",
                return_value="DOCKET-6",
            ),
            patch(_flow_symbol("time.sleep")) as sleep,
        ):
            result = CaseLawRouter.handle_main_opinion_fields(
                router,
                {
                    "FileName": "main.pdf",
                    "SourceDetail": "",
                    "Comments": "Retry note",
                },
                object(),
                85,
                "mapping.xlsx",
            )

        self.assertIsNone(result)
        self.assertEqual(2, comments.clear.call_count)
        comments.send_keys.assert_called_once_with("Retry note")
        sleep.assert_called_once_with(1)

    @unittest.skipUnless(
        importlib.util.find_spec(
            "core.router_modes.main_opinion_fields_selenium"
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
            and node.name == "handle_main_opinion_fields"
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
            "core.router_modes.main_opinion_fields_selenium"
        ),
        "module boundary applies after extraction",
    )
    def test_extracted_module_delegates_related_lni_and_attachment_work(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "main_opinion_fields_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("router.handle_related_ln_is(", source)
        self.assertIn("resolve_source_detail", source)
        self.assertIn("Non-interactable IRT Form", source)
        self.assertNotIn("get_related_counsel_lnis", source)
        self.assertNotIn("attachment_files", source)
        for unrelated_mode in ("MSPB", "ITC", "IRSPLR", "OHTAX0", "MNSUTB"):
            with self.subTest(unrelated_mode=unrelated_mode):
                self.assertNotIn(unrelated_mode, source)


if __name__ == "__main__":
    unittest.main()
