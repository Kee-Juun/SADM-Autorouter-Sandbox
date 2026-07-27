"""No-driver contract tests for the Phase 6E OHTAX0 row wrapper."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.router_modes.ohtax0_batch_row import (
    Ohtax0RowOutcome,
    process_ohtax0_document_row,
)
from core.smducar_router import CaseLawRouter


class Ohtax0BatchRowTests(unittest.TestCase):
    def _dependencies(self, metadata=object()):
        router = Mock()
        router.search_lni.return_value = True
        router.check_result_available.return_value = True
        handler = Mock()
        handler.extract_metadata.return_value = metadata
        row = {
            "FileName": "ohtax0.pdf",
            "CourtCode": "OHTAX0",
            "LNI": "LNI-1",
        }
        return router, handler, row

    def test_success_preserves_attempt_search_extract_record_and_click(self):
        metadata = object()
        router, handler, row = self._dependencies(metadata)

        outcome = process_ohtax0_document_row(
            router,
            handler,
            17,
            row,
            "LNI-1",
        )

        self.assertEqual(
            Ohtax0RowOutcome(
                continue_to_form=True,
                metadata=metadata,
                row_status=None,
            ),
            outcome,
        )
        router.search_lni.assert_called_once_with("LNI-1")
        router.check_result_available.assert_called_once_with()
        handler.extract_metadata.assert_called_once_with(router, row, 17)
        self.assertEqual(
            [
                call(
                    router,
                    17,
                    row,
                    "LNI-1",
                    metadata_status="Attempted",
                ),
                call(
                    router,
                    17,
                    row,
                    "LNI-1",
                    metadata=metadata,
                    metadata_status="Extracted",
                ),
            ],
            handler.record_metadata.call_args_list,
        )
        router.click_matching_result.assert_called_once_with()

    def test_search_failure_preserves_short_circuit_and_status(self):
        router, handler, row = self._dependencies()
        router.search_lni.return_value = False

        outcome = process_ohtax0_document_row(
            router,
            handler,
            19,
            row,
            "LNI-1",
        )

        self.assertEqual(
            Ohtax0RowOutcome(
                continue_to_form=False,
                metadata=None,
                row_status="ERROR: LNI NOT FOUND",
            ),
            outcome,
        )
        router.check_result_available.assert_not_called()
        handler.extract_metadata.assert_not_called()
        self.assertEqual(
            [
                call(
                    router,
                    19,
                    row,
                    "LNI-1",
                    metadata_status="Attempted",
                ),
                call(
                    router,
                    19,
                    row,
                    "LNI-1",
                    metadata_status="Search Failed",
                ),
            ],
            handler.record_metadata.call_args_list,
        )
        router.click_matching_result.assert_not_called()

    def test_unavailable_result_records_search_failure(self):
        router, handler, row = self._dependencies()
        router.check_result_available.return_value = False

        outcome = process_ohtax0_document_row(
            router,
            handler,
            21,
            row,
            "LNI-1",
        )

        self.assertFalse(outcome.continue_to_form)
        self.assertEqual("ERROR: LNI NOT FOUND", outcome.row_status)
        handler.extract_metadata.assert_not_called()
        handler.record_metadata.assert_has_calls(
            [
                call(
                    router,
                    21,
                    row,
                    "LNI-1",
                    metadata_status="Attempted",
                ),
                call(
                    router,
                    21,
                    row,
                    "LNI-1",
                    metadata_status="Search Failed",
                ),
            ]
        )

    def test_missing_metadata_returns_policy_status_without_result_click(self):
        router, handler, row = self._dependencies(metadata=None)

        outcome = process_ohtax0_document_row(
            router,
            handler,
            23,
            row,
            "LNI-1",
        )

        self.assertEqual(
            Ohtax0RowOutcome(
                continue_to_form=False,
                metadata=None,
                row_status="SKIPPED: OHTAX0 PDF DATA NOT FOUND",
            ),
            outcome,
        )
        handler.record_metadata.assert_any_call(
            router,
            23,
            row,
            "LNI-1",
            metadata_status="Not Extracted",
        )
        router.click_matching_result.assert_not_called()

    def test_dependency_errors_propagate_to_outer_batch_boundary(self):
        router, handler, row = self._dependencies()
        handler.extract_metadata.side_effect = RuntimeError("extract failed")

        with self.assertRaisesRegex(RuntimeError, "extract failed"):
            process_ohtax0_document_row(
                router,
                handler,
                25,
                row,
                "LNI-1",
            )

    def test_router_method_is_a_thin_compatibility_wrapper(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        handler = object()
        row = object()
        expected = object()

        with patch(
            "core.smducar_router.run_process_ohtax0_document_row",
            return_value=expected,
        ) as delegated:
            actual = CaseLawRouter.process_ohtax0_document_row(
                router,
                handler,
                27,
                row,
                "LNI-1",
            )

        self.assertIs(expected, actual)
        delegated.assert_called_once_with(
            router,
            handler,
            27,
            row,
            "LNI-1",
        )

    def test_module_has_no_selenium_pandas_router_or_buffer_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "ohtax0_batch_row.py"
        )
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported_modules = {
            alias.name
            for node in tree.body
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        imported_modules.update(
            node.module
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module
        )

        for forbidden in (
            "selenium",
            "pandas",
            "smducar_router",
            "smducar_config",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertFalse(
                    any(
                        module == forbidden
                        or module.startswith(f"{forbidden}.")
                        for module in imported_modules
                    )
                )
        self.assertNotIn("status_updates_buffer", source)
        self.assertNotIn("mspb_metadata_buffer", source)


if __name__ == "__main__":
    unittest.main()
