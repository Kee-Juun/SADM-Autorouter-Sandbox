"""No-driver contracts for Phase 6G post-form row finalization."""

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch


class _FailingStatus(dict):
    def __setitem__(self, key, value):
        raise RuntimeError("status failed")


class BatchRowFinalizationTests(unittest.TestCase):
    def test_replaces_processing_status_and_returns_immutable_increment(self):
        from core.router_modes.batch_row_finalization import (
            finalize_batch_row,
        )

        status_buffer = {7: "PROCESSING"}
        clock = Mock(return_value=15.5)

        outcome = finalize_batch_row(
            7,
            10,
            " related lni error ",
            status_buffer=status_buffer,
            clock=clock,
        )

        self.assertEqual("RELATED LNI ERROR", status_buffer[7])
        self.assertEqual("RELATED LNI ERROR", outcome.replacement_status)
        self.assertEqual(5.5, outcome.duration)
        self.assertEqual(0, outcome.processed_increment)
        clock.assert_called_once_with()
        with self.assertRaises(FrozenInstanceError):
            outcome.duration = 0

    def test_completed_form_status_does_not_replace_processing(self):
        from core.router_modes.batch_row_finalization import (
            finalize_batch_row,
        )

        status_buffer = {7: "PROCESSING"}

        outcome = finalize_batch_row(
            7,
            10,
            "DONE",
            status_buffer=status_buffer,
            clock=Mock(return_value=12),
        )

        self.assertEqual("PROCESSING", status_buffer[7])
        self.assertIsNone(outcome.replacement_status)
        self.assertEqual(2, outcome.duration)

    def test_existing_nonprocessing_status_is_preserved(self):
        from core.router_modes.batch_row_finalization import (
            finalize_batch_row,
        )

        status_buffer = {7: "RELATED LNI FIELD LOCKED"}

        outcome = finalize_batch_row(
            7,
            10,
            "custom form error",
            status_buffer=status_buffer,
            clock=Mock(return_value=12),
        )

        self.assertEqual("RELATED LNI FIELD LOCKED", status_buffer[7])
        self.assertIsNone(outcome.replacement_status)

    def test_status_write_failure_occurs_before_clock_read(self):
        from core.router_modes.batch_row_finalization import (
            finalize_batch_row,
        )

        status_buffer = _FailingStatus({7: "PROCESSING"})
        clock = Mock(return_value=12)

        with self.assertRaisesRegex(RuntimeError, "status failed"):
            finalize_batch_row(
                7,
                10,
                "ERROR",
                status_buffer=status_buffer,
                clock=clock,
            )

        clock.assert_not_called()

    def test_clock_failure_occurs_after_status_replacement(self):
        from core.router_modes.batch_row_finalization import (
            finalize_batch_row,
        )

        status_buffer = {7: "PROCESSING"}
        clock = Mock(side_effect=RuntimeError("clock failed"))

        with self.assertRaisesRegex(RuntimeError, "clock failed"):
            finalize_batch_row(
                7,
                10,
                "ERROR",
                status_buffer=status_buffer,
                clock=clock,
            )

        self.assertEqual("ERROR", status_buffer[7])

    def test_logs_successful_route_duration(self):
        from core.router_modes.batch_row_finalization import (
            log_batch_row_duration,
        )

        with patch(
            "core.router_modes.batch_row_finalization.logging.info"
        ) as log:
            result = log_batch_row_duration("LNI-1", 2.345, "DONE")

        self.assertIsNone(result)
        log.assert_called_once_with(
            "[LNI PROCESSING TIME] LNI LNI-1 routed and saved in "
            "2.35 seconds."
        )

    def test_module_has_no_selenium_config_buffer_or_router_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "batch_row_finalization.py"
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
            "time",
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
        self.assertNotIn("error_log_entries", source)


if __name__ == "__main__":
    unittest.main()
