"""No-driver characterization tests for CaseLawRouter.process_rows()."""

import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import pandas as pd
from pandas.testing import assert_frame_equal

from core.smducar_config import error_log_entries
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


def _router(driver=None):
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = driver or _TrackingDriver(["main"])
    router.set_status = Mock()
    router.process_batch = Mock(return_value=(2, 5))
    return router


def _frames():
    full = pd.DataFrame(
        [
            {
                "FileName": "main.pdf",
                "CourtCode": "",
                "LNI": "LNI-1",
                "Status": "",
            }
        ],
        index=[5],
    )
    counsel = full.iloc[0:0].copy()
    main = full.copy()
    return full, counsel, main


class ProcessRowsCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        error_log_entries.clear()

    def test_each_document_mode_preserves_single_batch_dispatch(self):
        cases = (
            (
                "mspb",
                {"mspb_mode": True},
                "mspb",
                {"mspb_mode": True},
                "MSPB Batch Started",
                "MSPB Batch Processed",
            ),
            (
                "itc",
                {"itc_mode": True},
                "itc",
                {},
                "ITC Batch Started",
                "ITC Batch Processed",
            ),
            (
                "irsplr",
                {"irsplr_mode": True},
                "irsplr",
                {"irsplr_mode": True},
                "IRSPLR Batch Started",
                "IRSPLR Batch Processed",
            ),
            (
                "ohtax0",
                {"ohtax0_mode": True},
                "ohtax0",
                {"ohtax0_mode": True},
                "OHTAX0 Batch Started",
                "OHTAX0 Batch Processed",
            ),
            (
                "mnsutb",
                {"mnsutb_mode": True},
                "mnsutb",
                {"mnsutb_mode": True},
                "MNSUTB Batch Started",
                "MNSUTB Batch Processed",
            ),
        )

        for (
            key,
            mode_kwargs,
            batch_type,
            expected_kwargs,
            started,
            processed,
        ) in cases:
            with self.subTest(mode=key):
                full, counsel, filtered_main = _frames()
                router = _router()

                with patch(
                    "core.smducar_router.filter_mapping_data",
                    return_value=(counsel, filtered_main),
                ):
                    returned_counsel, returned_main = (
                        CaseLawRouter.process_rows(
                            router,
                            full,
                            "mapping.xlsx",
                            "progress-callback",
                            **mode_kwargs,
                        )
                    )

                router.process_batch.assert_called_once()
                args = router.process_batch.call_args.args
                expected_batch_rows = (
                    filtered_main if key == "mspb" else full
                )
                assert_frame_equal(args[0], expected_batch_rows)
                self.assertIs(full, args[1])
                self.assertEqual("mapping.xlsx", args[2])
                self.assertEqual("progress-callback", args[3])
                self.assertEqual(batch_type, args[4])
                self.assertEqual(False, args[5])
                self.assertEqual(False, args[6])
                self.assertEqual(
                    expected_kwargs,
                    router.process_batch.call_args.kwargs,
                )
                self.assertEqual(
                    [call(started), call(processed)],
                    router.set_status.call_args_list,
                )
                if key == "mspb":
                    assert_frame_equal(returned_counsel, counsel)
                    assert_frame_equal(returned_main, filtered_main)
                else:
                    self.assertTrue(returned_counsel.empty)
                    assert_frame_equal(returned_main, full)

    def test_contradictory_document_flags_preserve_mspb_precedence(self):
        full, counsel, main = _frames()
        router = _router()

        with patch(
            "core.smducar_router.filter_mapping_data",
            return_value=(counsel, main),
        ):
            CaseLawRouter.process_rows(
                router,
                full,
                "mapping.xlsx",
                None,
                mspb_mode=True,
                itc_mode=True,
                irsplr_mode=True,
                ohtax0_mode=True,
                mnsutb_mode=True,
            )

        self.assertEqual("mspb", router.process_batch.call_args.args[4])
        self.assertEqual(
            {"mspb_mode": True},
            router.process_batch.call_args.kwargs,
        )

    def test_shared_run_preserves_counsel_defer_main_order_and_statuses(self):
        full, counsel, main = _frames()
        deferred_main = main.copy()
        router = _router()
        router.process_batch.side_effect = [(2, 4), (3, 6)]
        deferred_rows = [5]

        with (
            patch(
                "core.smducar_router.filter_mapping_data",
                return_value=(counsel, main),
            ),
            patch(
                "core.router_modes.shared_run_dispatch.defer_main_rows_with_failed_counsel",
                return_value=(deferred_main, deferred_rows),
            ) as defer,
        ):
            returned = CaseLawRouter.process_rows(
                router,
                full,
                "mapping.xlsx",
                "progress",
                dar_mode=True,
                wc_mode=True,
            )

        self.assertEqual(2, router.process_batch.call_count)
        first, second = router.process_batch.call_args_list
        assert_frame_equal(first.args[0], counsel)
        self.assertEqual(
            (
                full,
                "mapping.xlsx",
                "progress",
                "counsel",
                True,
                True,
            ),
            first.args[1:],
        )
        assert_frame_equal(second.args[0], deferred_main)
        self.assertEqual(
            (
                full,
                "mapping.xlsx",
                "progress",
                "main",
                True,
                True,
            ),
            second.args[1:],
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
                call("Success!"),
            ],
            router.set_status.call_args_list,
        )
        self.assertIsNotNone(router._last_success_log_time)
        self.assertFalse(router._success_message_dismissed)
        assert_frame_equal(returned[0], counsel)
        assert_frame_equal(returned[1], deferred_main)

    def test_shared_run_closes_all_extra_windows_before_main_batch(self):
        full, counsel, main = _frames()
        driver = _TrackingDriver(["main", "extra-1", "extra-2"])
        router = _router(driver)

        with (
            patch(
                "core.smducar_router.filter_mapping_data",
                return_value=(counsel, main),
            ),
            patch(
                "core.router_modes.shared_run_dispatch.defer_main_rows_with_failed_counsel",
                return_value=(main, []),
            ),
        ):
            CaseLawRouter.process_rows(
                router,
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

    def test_error_report_is_written_only_through_existing_boundary(self):
        full, counsel, main = _frames()
        router = _router()
        error_log_entries.append(
            {
                "Row": 7,
                "LNI": "LNI-ERR",
                "File Name": "bad.pdf",
                "Status": "ERROR",
                "Error Message": "boom",
            }
        )
        virtual_home = Path("virtual-home")

        with (
            patch(
                "core.smducar_router.filter_mapping_data",
                return_value=(counsel, main),
            ),
            patch(
                "core.router_modes.shared_run_dispatch.defer_main_rows_with_failed_counsel",
                return_value=(main, []),
            ),
            patch.object(Path, "home", return_value=virtual_home),
            patch.object(Path, "mkdir") as mkdir,
            patch("pandas.DataFrame.to_excel") as to_excel,
        ):
            CaseLawRouter.process_rows(
                router,
                full,
                "mapping.xlsx",
                None,
            )

        mkdir.assert_called_once_with(parents=True, exist_ok=True)
        to_excel.assert_called_once()
        report_path = to_excel.call_args.args[0]
        self.assertIn("Error Reports", str(report_path))
        self.assertIn("Error Report - ", str(report_path))
        self.assertEqual({"index": False}, to_excel.call_args.kwargs)

    def test_filter_failure_returns_two_empty_dataframes(self):
        full, _, _ = _frames()
        router = _router()

        with patch(
            "core.smducar_router.filter_mapping_data",
            side_effect=RuntimeError("filter failed"),
        ):
            counsel, main = CaseLawRouter.process_rows(
                router,
                full,
                "mapping.xlsx",
                None,
            )

        self.assertTrue(counsel.empty)
        self.assertTrue(main.empty)
        router.process_batch.assert_not_called()

    def test_document_batch_failure_is_swallowed_as_empty_return_pair(self):
        full, counsel, main = _frames()
        router = _router()
        router.process_batch.side_effect = RuntimeError("batch failed")

        with patch(
            "core.smducar_router.filter_mapping_data",
            return_value=(counsel, main),
        ):
            returned_counsel, returned_main = CaseLawRouter.process_rows(
                router,
                full,
                "mapping.xlsx",
                None,
                itc_mode=True,
            )

        self.assertTrue(returned_counsel.empty)
        self.assertTrue(returned_main.empty)
        router.set_status.assert_called_once_with("ITC Batch Started")


if __name__ == "__main__":
    unittest.main()
