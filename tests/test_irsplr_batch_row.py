"""No-driver contract tests for the Phase 6E IRSPLR row wrapper."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.router_modes.irsplr_batch_row import (
    IrsplrRowOutcome,
    process_irsplr_document_row,
)
from core.smducar_router import CaseLawRouter


class IrsplrBatchRowTests(unittest.TestCase):
    def _dependencies(self, metadata=object()):
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
        row = {
            "FileName": "12-1234.pdf",
            "CourtCode": "FDIRSPLR",
            "LNI": "LNI-1",
        }
        return router, handler, row, events

    def test_success_records_extracted_metadata_then_clicks(self):
        metadata = object()
        router, handler, row, events = self._dependencies(metadata)

        with patch(
            "core.router_modes.irsplr_batch_row."
            "build_irsplr_unreadable_fallback_metadata"
        ) as build_fallback:
            outcome = process_irsplr_document_row(
                router,
                handler,
                17,
                row,
                "LNI-1",
            )

        self.assertEqual(
            IrsplrRowOutcome(
                continue_to_form=True,
                metadata=metadata,
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
                "record:Extracted",
                "click",
            ],
            events,
        )
        build_fallback.assert_not_called()
        handler.record_metadata.assert_called_with(
            router,
            17,
            row,
            "LNI-1",
            metadata=metadata,
            metadata_status="Extracted",
        )

    def test_missing_metadata_builds_fallback_and_continues_to_form(self):
        fallback = object()
        router, handler, row, events = self._dependencies(metadata=None)

        with patch(
            "core.router_modes.irsplr_batch_row."
            "build_irsplr_unreadable_fallback_metadata",
            side_effect=lambda **kwargs: (
                events.append("fallback") or fallback
            ),
        ) as build_fallback:
            outcome = process_irsplr_document_row(
                router,
                handler,
                19,
                row,
                "LNI-1",
            )

        self.assertEqual(
            IrsplrRowOutcome(
                continue_to_form=True,
                metadata=fallback,
                row_status=None,
            ),
            outcome,
        )
        build_fallback.assert_called_once_with(
            filename_hint="12-1234.pdf",
            court_code_hint="FDIRSPLR",
        )
        self.assertEqual(
            [
                "record:Attempted",
                "search",
                "available",
                "extract",
                "fallback",
                "record:Unreadable PDF Fallback",
                "click",
            ],
            events,
        )
        handler.record_metadata.assert_called_with(
            router,
            19,
            row,
            "LNI-1",
            metadata=fallback,
            metadata_status="Unreadable PDF Fallback",
        )

    def test_falsey_fallback_still_preserves_legacy_continuation(self):
        router, handler, row, _ = self._dependencies(metadata=None)

        with patch(
            "core.router_modes.irsplr_batch_row."
            "build_irsplr_unreadable_fallback_metadata",
            return_value=None,
        ):
            outcome = process_irsplr_document_row(
                router,
                handler,
                20,
                row,
                "LNI-1",
            )

        self.assertTrue(outcome.continue_to_form)
        self.assertIsNone(outcome.metadata)
        handler.record_metadata.assert_called_with(
            router,
            20,
            row,
            "LNI-1",
            metadata=None,
            metadata_status="Unreadable PDF Fallback",
        )
        router.click_matching_result.assert_called_once_with()

    def test_search_failure_preserves_short_circuit_and_status(self):
        router, handler, row, events = self._dependencies()
        router.search_lni.side_effect = lambda lni: (
            events.append("search") or False
        )

        outcome = process_irsplr_document_row(
            router,
            handler,
            21,
            row,
            "LNI-1",
        )

        self.assertEqual(
            IrsplrRowOutcome(
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
            ],
            handler.record_metadata.call_args_list,
        )

    def test_unavailable_result_records_search_failure(self):
        router, handler, row, events = self._dependencies()
        router.check_result_available.side_effect = lambda: (
            events.append("available") or False
        )

        outcome = process_irsplr_document_row(
            router,
            handler,
            23,
            row,
            "LNI-1",
        )

        self.assertFalse(outcome.continue_to_form)
        self.assertEqual("ERROR: LNI NOT FOUND", outcome.row_status)
        handler.extract_metadata.assert_not_called()
        router.click_matching_result.assert_not_called()

    def test_fallback_errors_propagate_to_outer_batch_boundary(self):
        router, handler, row, _ = self._dependencies(metadata=None)

        with (
            patch(
                "core.router_modes.irsplr_batch_row."
                "build_irsplr_unreadable_fallback_metadata",
                side_effect=RuntimeError("fallback failed"),
            ),
            self.assertRaisesRegex(RuntimeError, "fallback failed"),
        ):
            process_irsplr_document_row(
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
            "core.smducar_router.run_process_irsplr_document_row",
            return_value=expected,
        ) as delegated:
            actual = CaseLawRouter.process_irsplr_document_row(
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
            / "irsplr_batch_row.py"
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
