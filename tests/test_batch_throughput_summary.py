"""No-driver contracts for the Phase 6G batch throughput summary."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class BatchThroughputSummaryTests(unittest.TestCase):
    def test_logs_exact_legacy_summary_and_calculations(self):
        from core.router_modes.batch_throughput import (
            log_batch_throughput_summary,
        )

        clock = Mock(return_value=160)

        with patch(
            "core.router_modes.batch_throughput.logging.info"
        ) as log:
            result = log_batch_throughput_summary(
                processed_count=2,
                total_duration=5,
                batch_start_time=100,
                batch_type="main",
                clock=clock,
            )

        self.assertIsNone(result)
        clock.assert_called_once_with()
        log.assert_called_once_with(
            "[AVERAGE BATCH PROCESSING TIME - LNI/HOUR ESTIMATE] "
            "Processed 2 main LNIs in 1m 0s "
            "(Avg: 2.50s/LNI → Est. 1440 LNIs/hour)"
        )

    def test_preserves_integer_elapsed_truncation(self):
        from core.router_modes.batch_throughput import (
            log_batch_throughput_summary,
        )

        with patch(
            "core.router_modes.batch_throughput.logging.info"
        ) as log:
            log_batch_throughput_summary(
                processed_count=3,
                total_duration=4,
                batch_start_time=10.9,
                batch_type="counsel",
                clock=Mock(return_value=72.8),
            )

        log.assert_called_once_with(
            "[AVERAGE BATCH PROCESSING TIME - LNI/HOUR ESTIMATE] "
            "Processed 3 counsel LNIs in 1m 1s "
            "(Avg: 1.33s/LNI → Est. 2700 LNIs/hour)"
        )

    def test_zero_duration_raises_before_final_clock_read(self):
        from core.router_modes.batch_throughput import (
            log_batch_throughput_summary,
        )

        clock = Mock(return_value=160)

        with (
            patch(
                "core.router_modes.batch_throughput.logging.info"
            ) as log,
            self.assertRaises(ZeroDivisionError),
        ):
            log_batch_throughput_summary(
                processed_count=1,
                total_duration=0,
                batch_start_time=100,
                batch_type="main",
                clock=clock,
            )

        clock.assert_not_called()
        log.assert_not_called()

    def test_final_clock_error_propagates_without_logging(self):
        from core.router_modes.batch_throughput import (
            log_batch_throughput_summary,
        )

        clock = Mock(side_effect=RuntimeError("clock failed"))

        with (
            patch(
                "core.router_modes.batch_throughput.logging.info"
            ) as log,
            self.assertRaisesRegex(RuntimeError, "clock failed"),
        ):
            log_batch_throughput_summary(
                processed_count=1,
                total_duration=2,
                batch_start_time=100,
                batch_type="main",
                clock=clock,
            )

        log.assert_not_called()

    def test_module_has_no_runtime_state_or_selenium_dependencies(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "batch_throughput.py"
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
        self.assertNotIn("mspb_metadata_buffer", source)
        self.assertNotIn("error_log_entries", source)


if __name__ == "__main__":
    unittest.main()
