"""Unit tests for pure router batch policies."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.router_modes.batch_policy import (
    DOCUMENT_BATCH_POLICIES,
    MISSING_METADATA_POLICIES,
    completed_row_status,
    emit_batch_progress,
    form_status_replacement,
    get_document_batch_policy,
    get_missing_metadata_policy,
    is_progress_batch,
)


class BatchPolicyTests(unittest.TestCase):
    def test_progress_batch_membership_matches_legacy_labels(self):
        for batch_type in (
            "counsel",
            "main",
            "mspb",
            "itc",
            "irsplr",
            "ohtax0",
            "mnsutb",
        ):
            with self.subTest(batch_type=batch_type):
                self.assertTrue(is_progress_batch(batch_type))

        for batch_type in ("", None, "unknown", "MAIN"):
            with self.subTest(batch_type=batch_type):
                self.assertFalse(is_progress_batch(batch_type))

    def test_emit_batch_progress_calls_supported_callback_exactly(self):
        callback = Mock()

        emitted = emit_batch_progress(callback, "main", 2, 5)

        self.assertTrue(emitted)
        callback.assert_called_once_with("main", 2, 5)

    def test_emit_batch_progress_skips_unsupported_label(self):
        callback = Mock()

        emitted = emit_batch_progress(callback, "unknown", 2, 5)

        self.assertFalse(emitted)
        callback.assert_not_called()

    def test_emit_batch_progress_skips_missing_callback(self):
        self.assertFalse(emit_batch_progress(None, "main", 2, 5))

    def test_completed_row_status_preserves_exact_normalization(self):
        self.assertEqual("DONE", completed_row_status(" done "))
        self.assertEqual(
            "ALREADY PROCESSED",
            completed_row_status("already processed"),
        )
        for status in (None, "", "PROCESSING", "nan", 0):
            with self.subTest(status=status):
                self.assertIsNone(completed_row_status(status))

    def test_form_status_replaces_only_buffered_processing(self):
        self.assertEqual(
            "RELATED LNI ERROR",
            form_status_replacement(
                " processing ",
                " related lni error ",
            ),
        )
        self.assertIsNone(form_status_replacement("", "ERROR"))
        self.assertIsNone(form_status_replacement("DONE", "ERROR"))
        self.assertIsNone(form_status_replacement("PROCESSING", "DONE"))
        self.assertIsNone(
            form_status_replacement(
                "PROCESSING",
                "ALREADY PROCESSED",
            )
        )
        self.assertIsNone(form_status_replacement("PROCESSING", None))
        self.assertIsNone(form_status_replacement("PROCESSING", ""))

    def test_missing_metadata_policies_preserve_mode_asymmetry(self):
        expected = {
            "mspb": (
                "skip",
                "Not Extracted",
                "SKIPPED: MSPB PDF DATA NOT FOUND",
            ),
            "itc": (
                "skip",
                "Not Extracted",
                "SKIPPED: ITC PDF DATA NOT FOUND",
            ),
            "irsplr": (
                "fallback",
                "Unreadable PDF Fallback",
                None,
            ),
            "ohtax0": (
                "skip",
                "Not Extracted",
                "SKIPPED: OHTAX0 PDF DATA NOT FOUND",
            ),
            "mnsutb": (
                "skip",
                "Not Extracted",
                "SKIPPED: MNSUTB PDF DATA NOT FOUND",
            ),
        }

        self.assertEqual(tuple(expected), tuple(MISSING_METADATA_POLICIES))
        for mode_key, values in expected.items():
            with self.subTest(mode=mode_key):
                policy = get_missing_metadata_policy(mode_key)
                self.assertEqual(
                    values,
                    (
                        policy.action,
                        policy.metadata_status,
                        policy.row_status,
                    ),
                )

    def test_document_batch_policies_preserve_labels_and_flags(self):
        expected = {
            "mspb": (
                "MSPB Batch Started",
                "MSPB Batch Processed",
                True,
                "mspb_mode",
            ),
            "itc": (
                "ITC Batch Started",
                "ITC Batch Processed",
                False,
                None,
            ),
            "irsplr": (
                "IRSPLR Batch Started",
                "IRSPLR Batch Processed",
                False,
                "irsplr_mode",
            ),
            "ohtax0": (
                "OHTAX0 Batch Started",
                "OHTAX0 Batch Processed",
                False,
                "ohtax0_mode",
            ),
            "mnsutb": (
                "MNSUTB Batch Started",
                "MNSUTB Batch Processed",
                False,
                "mnsutb_mode",
            ),
        }

        self.assertEqual(tuple(expected), tuple(DOCUMENT_BATCH_POLICIES))
        for mode_key, values in expected.items():
            with self.subTest(mode=mode_key):
                policy = get_document_batch_policy(mode_key)
                self.assertEqual(mode_key, policy.batch_type)
                self.assertEqual(
                    values,
                    (
                        policy.started_status,
                        policy.processed_status,
                        policy.uses_filtered_main,
                        policy.process_batch_flag,
                    ),
                )

    def test_policy_mappings_are_immutable_and_unknown_keys_raise(self):
        with self.assertRaises(TypeError):
            MISSING_METADATA_POLICIES["new"] = object()
        with self.assertRaises(TypeError):
            DOCUMENT_BATCH_POLICIES["new"] = object()
        with self.assertRaises(KeyError):
            get_missing_metadata_policy("unknown")
        with self.assertRaises(KeyError):
            get_document_batch_policy("unknown")

    def test_module_has_no_runtime_or_mutable_state_dependencies(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "batch_policy.py"
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
            "pathlib",
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
