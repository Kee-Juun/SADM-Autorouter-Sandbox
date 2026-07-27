"""No-driver contract tests for the Phase 6E ITC row wrapper."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.router_modes.itc_batch_row import (
    ItcRowOutcome,
    process_itc_document_row,
)
from core.smducar_router import CaseLawRouter


class ItcBatchRowTests(unittest.TestCase):
    def _dependencies(self, metadata=object(), processed=object()):
        events = []
        router = Mock()
        router.search_lni.side_effect = lambda lni: (
            events.append("search") or True
        )
        router.check_result_available.side_effect = lambda: (
            events.append("available") or True
        )
        router.click_matching_result.side_effect = lambda: events.append(
            "click"
        )
        handler = Mock()
        handler.record_metadata.side_effect = lambda *args, **kwargs: (
            events.append(f"record:{kwargs['metadata_status']}")
        )
        handler.extract_metadata.side_effect = lambda *args: (
            events.append("extract") or metadata
        )
        handler.postprocess_metadata.side_effect = lambda *args: (
            events.append("postprocess") or processed
        )
        row = {
            "FileName": "itc.pdf",
            "CourtCode": "FDITC000",
            "LNI": "LNI-1",
        }
        return router, handler, row, events

    def test_success_preserves_postprocessing_order_and_processed_metadata(self):
        extracted = object()
        processed = object()
        router, handler, row, events = self._dependencies(
            extracted,
            processed,
        )

        outcome = process_itc_document_row(
            router,
            handler,
            17,
            row,
            "LNI-1",
        )

        self.assertEqual(
            ItcRowOutcome(
                continue_to_form=True,
                metadata=processed,
                row_status=None,
            ),
            outcome,
        )
        self.assertEqual(
            [
                "record:Attempted",
                "search",
                "available",
                "extract",
                "postprocess",
                "record:Extracted",
                "click",
            ],
            events,
        )
        handler.postprocess_metadata.assert_called_once_with(
            router,
            17,
            row,
            "LNI-1",
            extracted,
        )
        handler.record_metadata.assert_called_with(
            router,
            17,
            row,
            "LNI-1",
            metadata=processed,
            metadata_status="Extracted",
        )

    def test_postprocess_none_is_not_reclassified_as_missing_metadata(self):
        router, handler, row, events = self._dependencies(
            metadata=object(),
            processed=None,
        )

        outcome = process_itc_document_row(
            router,
            handler,
            18,
            row,
            "LNI-1",
        )

        self.assertTrue(outcome.continue_to_form)
        self.assertIsNone(outcome.metadata)
        self.assertIn("record:Extracted", events)
        self.assertNotIn("record:Not Extracted", events)
        router.click_matching_result.assert_called_once_with()

    def test_search_failure_preserves_short_circuit_and_status(self):
        router, handler, row, events = self._dependencies()
        router.search_lni.side_effect = lambda lni: (
            events.append("search") or False
        )

        outcome = process_itc_document_row(
            router,
            handler,
            19,
            row,
            "LNI-1",
        )

        self.assertEqual(
            ItcRowOutcome(
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

    def test_unavailable_result_records_search_failure(self):
        router, handler, row, events = self._dependencies()
        router.check_result_available.side_effect = lambda: (
            events.append("available") or False
        )

        outcome = process_itc_document_row(
            router,
            handler,
            21,
            row,
            "LNI-1",
        )

        self.assertFalse(outcome.continue_to_form)
        self.assertEqual("ERROR: LNI NOT FOUND", outcome.row_status)
        handler.extract_metadata.assert_not_called()
        handler.postprocess_metadata.assert_not_called()
        router.click_matching_result.assert_not_called()

    def test_missing_raw_metadata_skips_before_postprocessing(self):
        router, handler, row, events = self._dependencies(
            metadata=None,
        )

        outcome = process_itc_document_row(
            router,
            handler,
            23,
            row,
            "LNI-1",
        )

        self.assertEqual(
            ItcRowOutcome(
                continue_to_form=False,
                metadata=None,
                row_status="SKIPPED: ITC PDF DATA NOT FOUND",
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
        handler.postprocess_metadata.assert_not_called()
        router.click_matching_result.assert_not_called()
        self.assertNotIn("postprocess", events)

    def test_postprocessing_errors_propagate_to_outer_batch_boundary(self):
        router, handler, row, _ = self._dependencies()
        handler.postprocess_metadata.side_effect = RuntimeError(
            "postprocess failed"
        )

        with self.assertRaisesRegex(RuntimeError, "postprocess failed"):
            process_itc_document_row(
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
            "core.smducar_router.run_process_itc_document_row",
            return_value=expected,
        ) as delegated:
            actual = CaseLawRouter.process_itc_document_row(
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
            / "itc_batch_row.py"
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
