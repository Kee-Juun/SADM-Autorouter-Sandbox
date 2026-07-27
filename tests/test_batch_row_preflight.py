"""No-driver contracts for Phase 6G batch-row preflight."""

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch


def _prepare(
    router,
    row,
    *,
    status_buffer=None,
    mark_processing=None,
):
    from core.router_modes.batch_row_preflight import prepare_batch_row

    return prepare_batch_row(
        router,
        row,
        7,
        "mapping.xlsx",
        status_buffer=(
            status_buffer if status_buffer is not None else {}
        ),
        mark_processing=mark_processing or Mock(),
    )


class BatchRowPreflightTests(unittest.TestCase):
    def test_completed_row_preserves_status_log_and_skips_validation(self):
        router = Mock()
        row = {"Status": " done ", "LNI": "LNI-DONE"}
        status_buffer = {}
        mark = Mock()

        with patch(
            "core.router_modes.batch_row_preflight.logging.info"
        ) as log:
            outcome = _prepare(
                router,
                row,
                status_buffer=status_buffer,
                mark_processing=mark,
            )

        self.assertEqual("completed", outcome.action)
        self.assertFalse(outcome.should_process)
        self.assertIsNone(outcome.lni)
        self.assertEqual("DONE", outcome.row_status)
        self.assertEqual("DONE", status_buffer[7])
        log.assert_called_once_with(
            "Skipping completed row 9 with status: DONE."
        )
        router.validate_row.assert_not_called()
        mark.assert_not_called()
        with self.assertRaises(FrozenInstanceError):
            outcome.action = "changed"

    def test_invalid_lni_returns_skip_without_marking_processing(self):
        router = Mock()
        router.validate_row.return_value = None
        row = {"Status": "", "LNI": ""}
        mark = Mock()

        outcome = _prepare(
            router,
            row,
            mark_processing=mark,
        )

        self.assertEqual("invalid", outcome.action)
        self.assertFalse(outcome.should_process)
        self.assertIsNone(outcome.lni)
        router.validate_row.assert_called_once_with(
            row,
            7,
            "mapping.xlsx",
        )
        mark.assert_not_called()

    def test_processable_row_marks_processing_and_returns_exact_lni(self):
        router = Mock()
        lni = object()
        router.validate_row.return_value = lni
        row = {"Status": "", "LNI": "LNI-1"}
        mark = Mock()

        outcome = _prepare(
            router,
            row,
            mark_processing=mark,
        )

        self.assertEqual("process", outcome.action)
        self.assertTrue(outcome.should_process)
        self.assertIs(lni, outcome.lni)
        self.assertIsNone(outcome.row_status)
        mark.assert_called_once_with(7)

    def test_validation_failure_propagates_before_processing_mark(self):
        router = Mock()
        router.validate_row.side_effect = RuntimeError(
            "validation failed"
        )
        mark = Mock()

        with self.assertRaisesRegex(RuntimeError, "validation failed"):
            _prepare(
                router,
                {"Status": ""},
                mark_processing=mark,
            )

        mark.assert_not_called()

    def test_processing_mark_failure_propagates_after_validation(self):
        router = Mock()
        router.validate_row.return_value = "LNI-1"
        mark = Mock(side_effect=RuntimeError("mark failed"))

        with self.assertRaisesRegex(RuntimeError, "mark failed"):
            _prepare(
                router,
                {"Status": ""},
                mark_processing=mark,
            )

        router.validate_row.assert_called_once()

    def test_module_has_no_selenium_config_buffer_or_router_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "batch_row_preflight.py"
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
            "rerun_status",
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
        self.assertNotIn("mark_row_processing", source)


if __name__ == "__main__":
    unittest.main()
