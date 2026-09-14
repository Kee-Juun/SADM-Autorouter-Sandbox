"""No-driver contracts for the first Phase 6G shared-run slice."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import pandas as pd
from pandas.testing import assert_frame_equal

from core.router_modes.shared_run_dispatch import dispatch_shared_run
from core.smducar_router import CaseLawRouter


class _TrackingDriver:
    def __init__(self, handles):
        self.window_handles = list(handles)
        self.current = self.window_handles[0]
        self.closed = []
        self.switch_to = Mock()
        self.switch_to.window.side_effect = self._switch
        self.close = Mock(side_effect=self._close)

    def _switch(self, handle):
        self.current = handle

    def _close(self):
        self.closed.append(self.current)
        self.window_handles.remove(self.current)


def _frames():
    full = pd.DataFrame(
        [{"FileName": "main.pdf", "LNI": "LNI-1"}],
        index=[5],
    )
    counsel = full.iloc[0:0].copy()
    main = full.copy()
    return full, counsel, main


def _router(driver=None):
    router = Mock()
    router.driver = driver or _TrackingDriver(["main"])
    router.set_status = Mock()
    router.process_batch.side_effect = [(2, 4), (3, 6)]
    return router


class SharedRunDispatchTests(unittest.TestCase):
    def test_preserves_counsel_defer_main_order_statuses_and_outcome(self):
        full, counsel, main = _frames()
        deferred_main = main.copy()
        router = _router()

        with (
            patch(
                "core.router_modes.shared_run_dispatch."
                "defer_main_rows_with_failed_counsel",
                return_value=(deferred_main, [5]),
            ) as defer,
            patch(
                "core.router_modes.shared_run_dispatch.logging.info"
            ) as log,
        ):
            outcome = dispatch_shared_run(
                router,
                counsel,
                main,
                full,
                "mapping.xlsx",
                "progress",
                dar_mode=True,
                wc_mode=True,
            )

        self.assertEqual(2, router.process_batch.call_count)
        counsel_call, main_call = router.process_batch.call_args_list
        assert_frame_equal(counsel_call.args[0], counsel)
        self.assertEqual(
            (
                full,
                "mapping.xlsx",
                "progress",
                "counsel",
                True,
                True,
            ),
            counsel_call.args[1:],
        )
        assert_frame_equal(main_call.args[0], deferred_main)
        self.assertEqual(
            (
                full,
                "mapping.xlsx",
                "progress",
                "main",
                True,
                True,
            ),
            main_call.args[1:],
        )
        defer.assert_called_once_with(
            main,
            full,
            dar_mode=True,
            wc_mode=True,
        )
        self.assertEqual(
            [
                call("Counsel Batch Processed"),
                call("Main Opinion Batch Started"),
                call("Main Opinion Batch Processed"),
            ],
            router.set_status.call_args_list,
        )
        assert_frame_equal(outcome.counsel_df, counsel)
        assert_frame_equal(outcome.main_df, deferred_main)
        self.assertEqual(2, outcome.counsel_count)
        self.assertEqual(4, outcome.counsel_duration)
        self.assertEqual(3, outcome.main_count)
        self.assertEqual(6, outcome.main_duration)
        log.assert_any_call(
            "    - Overall Avg: %.1fs/LNI → Est. %d LNIs/hour",
            2.0,
            1800,
        )

    def test_closes_all_extra_windows_before_main_batch(self):
        full, counsel, main = _frames()
        driver = _TrackingDriver(["main", "extra-1", "extra-2"])
        router = _router(driver)

        with patch(
            "core.router_modes.shared_run_dispatch."
            "defer_main_rows_with_failed_counsel",
            return_value=(main, []),
        ):
            dispatch_shared_run(
                router,
                counsel,
                main,
                full,
                "mapping.xlsx",
                None,
            )

        self.assertEqual(["extra-2", "extra-1"], driver.closed)
        self.assertEqual(["main"], driver.window_handles)
        self.assertEqual(
            [
                call("extra-2"),
                call("main"),
                call("extra-1"),
                call("main"),
            ],
            driver.switch_to.window.call_args_list,
        )

    def test_cleanup_failure_is_best_effort_and_main_still_runs(self):
        full, counsel, main = _frames()
        driver = _TrackingDriver(["main", "extra"])
        driver.switch_to.window.side_effect = RuntimeError("switch failed")
        router = _router(driver)

        with patch(
            "core.router_modes.shared_run_dispatch."
            "defer_main_rows_with_failed_counsel",
            return_value=(main, []),
        ):
            outcome = dispatch_shared_run(
                router,
                counsel,
                main,
                full,
                "mapping.xlsx",
                None,
            )

        self.assertEqual(2, router.process_batch.call_count)
        self.assertEqual(3, outcome.main_count)

    def test_zero_total_count_emits_no_processing_summary(self):
        full, counsel, main = _frames()
        router = _router()
        router.process_batch.side_effect = [(0, 0), (0, 0)]

        with (
            patch(
                "core.router_modes.shared_run_dispatch."
                "defer_main_rows_with_failed_counsel",
                return_value=(main, []),
            ),
            patch(
                "core.router_modes.shared_run_dispatch.logging.info"
            ) as log,
        ):
            dispatch_shared_run(
                router,
                counsel,
                main,
                full,
                "mapping.xlsx",
                None,
            )

        self.assertNotIn(
            "[TOTAL AVERAGE PROCESSING TIME SUMMARY - LNI/HOUR "
            "ESTIMATE] TOTAL: %d LNIs successfully routed in %dm %ds",
            [item.args[0] for item in log.call_args_list],
        )

    def test_counsel_batch_errors_propagate_before_deferral(self):
        full, counsel, main = _frames()
        router = _router()
        router.process_batch.side_effect = RuntimeError("counsel failed")

        with (
            patch(
                "core.router_modes.shared_run_dispatch."
                "defer_main_rows_with_failed_counsel"
            ) as defer,
            self.assertRaisesRegex(RuntimeError, "counsel failed"),
        ):
            dispatch_shared_run(
                router,
                counsel,
                main,
                full,
                "mapping.xlsx",
                None,
            )

        defer.assert_not_called()

    def test_router_method_is_a_thin_compatibility_wrapper(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        full, counsel, main = _frames()
        expected = object()

        with patch(
            "core.smducar_router.run_dispatch_shared_run",
            return_value=expected,
        ) as delegated:
            actual = CaseLawRouter.dispatch_shared_run(
                router,
                counsel,
                main,
                full,
                "mapping.xlsx",
                "progress",
                dar_mode=True,
                wc_mode=True,
            )

        self.assertIs(expected, actual)
        delegated.assert_called_once_with(
            router,
            counsel,
            main,
            full,
            "mapping.xlsx",
            "progress",
            dar_mode=True,
            wc_mode=True,
        )

    def test_module_has_no_selenium_router_or_buffer_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "shared_run_dispatch.py"
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
