"""No-driver characterization tests for shared common-field preparation."""

import ast
import importlib.util
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.smducar_router import CaseLawRouter


class CommonFieldsSeleniumCharacterizationTests(unittest.TestCase):
    def _router(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.safe_fill_field = Mock()
        router.select_dropdown_by_visible_text_or_value = Mock()
        router.get_decision_date_from_received = Mock(
            return_value="01-31-2026"
        )
        return router

    def test_explicit_values_preserve_field_order_and_optional_court(self):
        router = self._router()

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            return_value="SHOULD-NOT-BE-USED",
        ) as formatter:
            result = CaseLawRouter.prepare_common_fields(
                router,
                "document.pdf",
                decision_date="02-03-2026",
                dar_mode=True,
                wc_mode=True,
                docket_override="OVERRIDE-123",
                court="FDITC000",
            )

        self.assertIsNone(result)
        formatter.assert_not_called()
        router.get_decision_date_from_received.assert_not_called()
        self.assertEqual(
            [
                call('//*[@id="numberOfPages"]', "1", "Number of Pages"),
                call(
                    '//*[@id="docketNumber"]',
                    "OVERRIDE-123",
                    "Docket Number",
                ),
                call(
                    '//*[@id="decisionDate"]',
                    "02-03-2026",
                    "Decision Date",
                ),
            ],
            router.safe_fill_field.call_args_list,
        )
        router.select_dropdown_by_visible_text_or_value.assert_called_once_with(
            '//*[@id="court"]',
            "FDITC000",
            "Court",
        )

    def test_missing_values_preserve_formatter_and_received_fallback(self):
        router = self._router()

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            return_value="DAR-456",
        ) as formatter:
            CaseLawRouter.prepare_common_fields(
                router,
                "dar_document.pdf",
                decision_date="",
                dar_mode=True,
                wc_mode=False,
            )

        formatter.assert_called_once_with(
            None,
            "dar_document.pdf",
            True,
            False,
        )
        router.get_decision_date_from_received.assert_called_once_with()
        self.assertEqual(
            call(
                '//*[@id="decisionDate"]',
                "01-31-2026",
                "Decision Date",
            ),
            router.safe_fill_field.call_args_list[2],
        )
        router.select_dropdown_by_visible_text_or_value.assert_not_called()

    def test_truthy_decision_date_and_absent_court_skip_optional_lookups(self):
        router = self._router()

        with patch.object(
            CaseLawRouter,
            "format_docket_number",
            return_value="SMD-789",
        ):
            CaseLawRouter.prepare_common_fields(
                router,
                "smd_document.pdf",
                decision_date="04-05-2026",
            )

        router.get_decision_date_from_received.assert_not_called()
        router.select_dropdown_by_visible_text_or_value.assert_not_called()

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.common_fields_selenium"),
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
            and node.name == "prepare_common_fields"
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
        importlib.util.find_spec("core.router_modes.common_fields_selenium"),
        "module boundary applies after extraction",
    )
    def test_extracted_module_remains_mode_neutral(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "common_fields_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("numberOfPages", source)
        self.assertIn("docketNumber", source)
        self.assertIn("decisionDate", source)
        self.assertIn('//*[@id="court"]', source)
        for mode_name in (
            "MSPB",
            "ITC",
            "IRSPLR",
            "OHTAX0",
            "MNSUTB",
            "SMD",
            "DAR",
        ):
            with self.subTest(mode_name=mode_name):
                self.assertNotIn(mode_name, source)


if __name__ == "__main__":
    unittest.main()
