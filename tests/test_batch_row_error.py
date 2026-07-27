"""No-driver contracts for Phase 6G generic batch-row error recording."""

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch


class _FailingEntries(list):
    def append(self, value):
        raise RuntimeError("append failed")


def _predicates(selected):
    return {
        "itc": Mock(return_value=selected == "itc"),
        "irsplr": Mock(return_value=selected == "irsplr"),
        "ohtax0": Mock(return_value=selected == "ohtax0"),
        "mnsutb": Mock(return_value=selected == "mnsutb"),
    }


def _record(
    router,
    row,
    *,
    selected=None,
    metadata_buffer=None,
    status_buffer=None,
    error_entries=None,
):
    from core.router_modes.batch_row_error import record_batch_row_error

    predicates = _predicates(selected)
    outcome = record_batch_row_error(
        router,
        9,
        row,
        RuntimeError("boom"),
        mspb_mode=selected == "mspb",
        metadata_buffer=metadata_buffer if metadata_buffer is not None else {},
        status_buffer=status_buffer if status_buffer is not None else {},
        error_entries=error_entries if error_entries is not None else [],
        is_itc_row=predicates["itc"],
        is_irsplr_row=predicates["irsplr"],
        is_ohtax0_row=predicates["ohtax0"],
        is_mnsutb_row=predicates["mnsutb"],
    )
    return outcome, predicates


class BatchRowErrorTests(unittest.TestCase):
    def test_preserves_mode_precedence_recorders_and_shared_status_lookup(self):
        method_names = {
            "mspb": "record_mspb_metadata",
            "itc": "record_itc_metadata",
            "irsplr": "record_irsplr_metadata",
            "ohtax0": "record_ohtax0_metadata",
            "mnsutb": "record_mnsutb_metadata",
        }
        row = {"LNI": "LNI-ERR", "FileName": "bad.pdf"}

        for selected, method_name in method_names.items():
            with self.subTest(mode=selected):
                router = Mock()
                status_buffer = {}
                error_entries = []
                metadata_buffer = {
                    9: {
                        "Metadata Status": (
                            "Extracted" if selected == "itc" else "Attempted"
                        )
                    }
                }

                with patch(
                    "core.router_modes.batch_row_error.logging.error"
                ) as log:
                    outcome, predicates = _record(
                        router,
                        row,
                        selected=selected,
                        metadata_buffer=metadata_buffer,
                        status_buffer=status_buffer,
                        error_entries=error_entries,
                    )

                expected_status = (
                    "Extracted" if selected == "itc" else "Error"
                )
                getattr(router, method_name).assert_called_once_with(
                    9,
                    row,
                    "LNI-ERR",
                    metadata_status=expected_status,
                )
                self.assertEqual(selected, outcome.mode_key)
                self.assertEqual(expected_status, outcome.metadata_status)
                self.assertEqual("ERROR", status_buffer[9])
                self.assertEqual("ERROR", error_entries[0]["Status"])
                log.assert_called_once_with("Error processing row 11")

                if selected == "mspb":
                    for predicate in predicates.values():
                        predicate.assert_not_called()

        with self.assertRaises(FrozenInstanceError):
            outcome.mode_key = "changed"

    def test_no_document_mode_still_records_status_and_error_entry(self):
        router = Mock()
        row = {"LNI": "LNI-ERR", "FileName": "bad.pdf"}
        status_buffer = {}
        error_entries = []

        outcome, predicates = _record(
            router,
            row,
            status_buffer=status_buffer,
            error_entries=error_entries,
        )

        self.assertIsNone(outcome.mode_key)
        self.assertIsNone(outcome.metadata_status)
        self.assertEqual("ERROR", status_buffer[9])
        self.assertEqual(
            {
                "Row": 11,
                "LNI": "LNI-ERR",
                "File Name": "bad.pdf",
                "Status": "ERROR",
                "Error Message": "boom",
            },
            error_entries[0],
        )
        for predicate in predicates.values():
            predicate.assert_called_once_with(row)

    def test_metadata_recorder_failure_prevents_buffers_and_propagates(self):
        router = Mock()
        router.record_mspb_metadata.side_effect = RuntimeError(
            "record failed"
        )
        status_buffer = {}
        error_entries = []

        with self.assertRaisesRegex(RuntimeError, "record failed"):
            _record(
                router,
                {"LNI": "LNI-ERR"},
                selected="mspb",
                status_buffer=status_buffer,
                error_entries=error_entries,
            )

        self.assertEqual({}, status_buffer)
        self.assertEqual([], error_entries)

    def test_error_entry_failure_occurs_after_status_update(self):
        status_buffer = {}

        with self.assertRaisesRegex(RuntimeError, "append failed"):
            _record(
                Mock(),
                {"LNI": "LNI-ERR"},
                status_buffer=status_buffer,
                error_entries=_FailingEntries(),
            )

        self.assertEqual("ERROR", status_buffer[9])

    def test_module_has_no_selenium_config_buffer_or_extractor_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "batch_row_error.py"
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
            "smducar_router",
            "smducar_config",
            "mspb_extractor",
            "itc_extractor",
            "irsplr_extractor",
            "ohtax0_extractor",
            "mnsutb_extractor",
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
        self.assertNotIn("error_log_entries", source)


if __name__ == "__main__":
    unittest.main()
