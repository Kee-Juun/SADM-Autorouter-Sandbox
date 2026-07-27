"""No-driver characterization tests for CaseLawRouter.process_batch()."""

import unittest
from unittest.mock import ANY, Mock, call, patch

import pandas as pd

from core.smducar_config import (
    error_log_entries,
    mspb_metadata_buffer,
    status_updates_buffer,
)
from core.smducar_router import CaseLawRouter, RouterSessionLostError


def _frame(rows=None, index=None):
    rows = rows or [
        {
            "FileName": "document.pdf",
            "CourtCode": "",
            "LNI": "LNI-1",
            "Status": "",
        }
    ]
    return pd.DataFrame(rows, index=index)


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.driver.window_handles = ["main"]
    router.safe_alert_accept = Mock()
    router.validate_row = Mock(return_value="LNI-1")
    router.handle_lni_search = Mock(return_value=True)
    router.search_lni = Mock(return_value=True)
    router.check_result_available = Mock(return_value=True)
    router.click_matching_result = Mock()
    router.open_and_process_form = Mock(return_value="DONE")
    router._should_refresh_retry_form_status = Mock(return_value=False)
    router._refresh_and_retry_current_row = Mock()
    router._mark_remaining_rows_after_router_session_loss = Mock()
    router.record_mspb_metadata = Mock()
    router.record_itc_metadata = Mock()
    router.record_irsplr_metadata = Mock()
    router.record_ohtax0_metadata = Mock()
    router.record_mnsutb_metadata = Mock()
    return router


def _handler(key, metadata=object()):
    handler = Mock()
    handler.key = key
    handler.extract_metadata.return_value = metadata
    handler.postprocess_metadata.return_value = metadata
    return handler


class ProcessBatchCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()
        mspb_metadata_buffer.clear()
        error_log_entries.clear()

    def test_shared_success_preserves_progress_timing_and_count(self):
        router = _router()
        frame = _frame(index=[7])
        progress = Mock()

        with (
            patch(
                "core.smducar_router.select_row_mode_handler",
                return_value=None,
            ),
            patch(
                "core.smducar_router.time.time",
                side_effect=[0, 10, 12, 15],
            ),
            patch("core.smducar_router.mark_row_processing") as mark,
            patch(
                "core.router_modes.batch_throughput.logging.info"
            ) as log,
        ):
            count, duration = CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                progress,
                "main",
            )

        self.assertEqual(1, count)
        self.assertEqual(2, duration)
        router.safe_alert_accept.assert_called_once_with()
        mark.assert_called_once_with(7)
        router.handle_lni_search.assert_called_once_with("LNI-1")
        router.open_and_process_form.assert_called_once()
        self.assertEqual(
            [call("main", 0, 1), call("main", 1, 1)],
            progress.call_args_list,
        )
        log.assert_any_call(
            "[AVERAGE BATCH PROCESSING TIME - LNI/HOUR ESTIMATE] "
            "Processed 1 main LNIs in 0m 15s "
            "(Avg: 2.00s/LNI → Est. 1800 LNIs/hour)"
        )
        log.assert_any_call(
            "[LNI PROCESSING TIME] LNI LNI-1 processed in "
            "2.00 seconds."
        )

    def test_completed_row_is_preserved_and_only_advances_progress(self):
        router = _router()
        frame = _frame(
            [
                {
                    "FileName": "done.pdf",
                    "CourtCode": "",
                    "LNI": "LNI-DONE",
                    "Status": " done ",
                }
            ],
            index=[11],
        )
        progress = Mock()

        count, duration = CaseLawRouter.process_batch(
            router,
            frame,
            frame,
            "mapping.xlsx",
            progress,
            "main",
        )

        self.assertEqual((0, 0), (count, duration))
        self.assertEqual("DONE", status_updates_buffer[11])
        router.validate_row.assert_not_called()
        self.assertEqual(
            [call("main", 0, 1), call("main", 1, 1)],
            progress.call_args_list,
        )

    def test_invalid_lni_skips_processing_but_advances_progress(self):
        router = _router()
        router.validate_row.return_value = None
        frame = _frame(index=[13])
        progress = Mock()

        with patch("core.smducar_router.mark_row_processing") as mark:
            result = CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                progress,
                "counsel",
            )

        self.assertEqual((0, 0), result)
        mark.assert_not_called()
        router.handle_lni_search.assert_not_called()
        self.assertEqual(
            [call("counsel", 0, 1), call("counsel", 1, 1)],
            progress.call_args_list,
        )

    def test_unknown_batch_label_emits_no_progress(self):
        router = _router()
        router.validate_row.return_value = None
        progress = Mock()
        frame = _frame()

        CaseLawRouter.process_batch(
            router,
            frame,
            frame,
            "mapping.xlsx",
            progress,
            "unknown",
        )

        progress.assert_not_called()

    def test_document_success_forwards_only_selected_metadata_slot(self):
        cases = (
            ("mspb", "mspb_metadata", True),
            ("itc", "itc_metadata", False),
            ("irsplr", "irsplr_metadata", False),
            ("ohtax0", "ohtax0_metadata", False),
            ("mnsutb", "mnsutb_metadata", False),
        )
        frame = _frame(index=[17])

        for key, metadata_keyword, mspb_mode in cases:
            with self.subTest(mode=key):
                status_updates_buffer.clear()
                router = _router()
                extracted = object()
                processed = object()
                handler = _handler(key, extracted)
                if key == "itc":
                    handler.postprocess_metadata.return_value = processed
                    expected_metadata = processed
                else:
                    expected_metadata = extracted

                with patch(
                    "core.smducar_router.select_row_mode_handler",
                    return_value=handler,
                ):
                    count, _ = CaseLawRouter.process_batch(
                        router,
                        frame,
                        frame,
                        "mapping.xlsx",
                        None,
                        key,
                        mspb_mode=mspb_mode,
                    )

                self.assertEqual(1, count)
                handler.record_metadata.assert_any_call(
                    router,
                    17,
                    ANY,
                    "LNI-1",
                    metadata_status="Attempted",
                )
                handler.record_metadata.assert_any_call(
                    router,
                    17,
                    ANY,
                    "LNI-1",
                    metadata=expected_metadata,
                    metadata_status="Extracted",
                )
                if key == "itc":
                    handler.postprocess_metadata.assert_called_once_with(
                        router,
                        17,
                        ANY,
                        "LNI-1",
                        extracted,
                    )
                router.click_matching_result.assert_called_once_with()
                kwargs = router.open_and_process_form.call_args.kwargs
                for slot in (
                    "mspb_metadata",
                    "itc_metadata",
                    "irsplr_metadata",
                    "ohtax0_metadata",
                    "mnsutb_metadata",
                ):
                    self.assertIs(
                        expected_metadata if slot == metadata_keyword else None,
                        kwargs[slot],
                    )

    def test_document_search_failure_records_and_skips_form(self):
        router = _router()
        router.search_lni.return_value = False
        handler = _handler("mspb")
        frame = _frame(index=[19])

        with patch(
            "core.smducar_router.select_row_mode_handler",
            return_value=handler,
        ):
            result = CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                None,
                "mspb",
                mspb_mode=True,
            )

        self.assertEqual((0, 0), result)
        self.assertEqual("ERROR: LNI NOT FOUND", status_updates_buffer[19])
        self.assertEqual(
            [
                call(
                    router,
                    19,
                    ANY,
                    "LNI-1",
                    metadata_status="Attempted",
                ),
                call(
                    router,
                    19,
                    ANY,
                    "LNI-1",
                    metadata_status="Search Failed",
                ),
            ],
            handler.record_metadata.call_args_list,
        )
        handler.extract_metadata.assert_not_called()
        router.open_and_process_form.assert_not_called()

    def test_missing_metadata_statuses_preserve_mode_asymmetry(self):
        cases = {
            "mspb": "SKIPPED: MSPB PDF DATA NOT FOUND",
            "itc": "SKIPPED: ITC PDF DATA NOT FOUND",
            "ohtax0": "SKIPPED: OHTAX0 PDF DATA NOT FOUND",
            "mnsutb": "SKIPPED: MNSUTB PDF DATA NOT FOUND",
        }
        frame = _frame(index=[23])

        for key, expected_status in cases.items():
            with self.subTest(mode=key):
                status_updates_buffer.clear()
                router = _router()
                handler = _handler(key, None)

                with patch(
                    "core.smducar_router.select_row_mode_handler",
                    return_value=handler,
                ):
                    result = CaseLawRouter.process_batch(
                        router,
                        frame,
                        frame,
                        "mapping.xlsx",
                        None,
                        key,
                        mspb_mode=(key == "mspb"),
                    )

                self.assertEqual((0, 0), result)
                self.assertEqual(expected_status, status_updates_buffer[23])
                handler.record_metadata.assert_any_call(
                    router,
                    23,
                    ANY,
                    "LNI-1",
                    metadata_status="Not Extracted",
                )
                router.click_matching_result.assert_not_called()
                router.open_and_process_form.assert_not_called()

    def test_irsplr_missing_metadata_uses_fallback_and_opens_form(self):
        router = _router()
        handler = _handler("irsplr", None)
        fallback = object()
        frame = _frame(index=[29])

        with (
            patch(
                "core.smducar_router.select_row_mode_handler",
                return_value=handler,
            ),
            patch(
                "core.router_modes.irsplr_batch_row."
                "build_irsplr_unreadable_fallback_metadata",
                return_value=fallback,
            ) as build_fallback,
        ):
            count, _ = CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                None,
                "irsplr",
                irsplr_mode=True,
            )

        self.assertEqual(1, count)
        build_fallback.assert_called_once_with(
            filename_hint="document.pdf",
            court_code_hint="",
        )
        handler.record_metadata.assert_any_call(
            router,
            29,
            ANY,
            "LNI-1",
            metadata=fallback,
            metadata_status="Unreadable PDF Fallback",
        )
        router.click_matching_result.assert_called_once_with()
        self.assertIs(
            fallback,
            router.open_and_process_form.call_args.kwargs[
                "irsplr_metadata"
            ],
        )

    def test_recoverable_form_status_retries_and_finalizes_processing(self):
        router = _router()
        router.open_and_process_form.return_value = "RELATED LNI ERROR"
        router._should_refresh_retry_form_status.return_value = True
        router._refresh_and_retry_current_row.return_value = (
            "related lni timeout"
        )
        frame = _frame(index=[31])

        with patch(
            "core.smducar_router.select_row_mode_handler",
            return_value=None,
        ):
            count, _ = CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                None,
                "main",
            )

        self.assertEqual(1, count)
        router._refresh_and_retry_current_row.assert_called_once()
        self.assertEqual(
            "RELATED LNI TIMEOUT",
            status_updates_buffer[31],
        )

    def test_existing_nonprocessing_status_is_not_overwritten(self):
        router = _router()
        router.open_and_process_form.side_effect = lambda *args, **kwargs: (
            status_updates_buffer.__setitem__(37, "RELATED LNI FIELD LOCKED")
            or "custom form error"
        )
        frame = _frame(index=[37])

        with patch(
            "core.smducar_router.select_row_mode_handler",
            return_value=None,
        ):
            CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                None,
                "main",
            )

        self.assertEqual(
            "RELATED LNI FIELD LOCKED",
            status_updates_buffer[37],
        )

    def test_generic_exception_marks_error_records_metadata_and_cleans(self):
        router = _router()
        original = RuntimeError("validation exploded")
        router.validate_row.side_effect = original
        frame = _frame(index=[41])

        result = CaseLawRouter.process_batch(
            router,
            frame,
            frame,
            "mapping.xlsx",
            None,
            "mspb",
            mspb_mode=True,
        )

        self.assertEqual((0, 0), result)
        self.assertEqual("ERROR", status_updates_buffer[41])
        router.record_mspb_metadata.assert_called_once_with(
            41,
            ANY,
            "LNI-1",
            metadata_status="Error",
        )
        self.assertEqual("ERROR", error_log_entries[0]["Status"])
        self.assertEqual(
            "validation exploded",
            error_log_entries[0]["Error Message"],
        )
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")

    def test_error_recording_failure_propagates_before_driver_cleanup(self):
        router = _router()
        router.validate_row.side_effect = RuntimeError(
            "validation exploded"
        )
        frame = _frame(index=[42])
        progress = Mock()

        with (
            patch(
                "core.smducar_router.record_batch_row_error",
                side_effect=RuntimeError("record failed"),
            ),
            self.assertRaisesRegex(RuntimeError, "record failed"),
        ):
            CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                progress,
                "mspb",
                mspb_mode=True,
            )

        router.driver.close.assert_not_called()
        router.driver.switch_to.window.assert_not_called()
        self.assertEqual(
            [call("mspb", 0, 1), call("mspb", 1, 1)],
            progress.call_args_list,
        )

    def test_session_loss_marks_remaining_forces_progress_and_stops(self):
        router = _router()
        lost = RouterSessionLostError("browser gone")
        router.open_and_process_form.side_effect = lost
        frame = _frame(
            [
                {
                    "FileName": "first.pdf",
                    "CourtCode": "",
                    "LNI": "LNI-1",
                    "Status": "",
                },
                {
                    "FileName": "second.pdf",
                    "CourtCode": "",
                    "LNI": "LNI-2",
                    "Status": "",
                },
            ],
            index=[43, 47],
        )
        progress = Mock()

        with patch(
            "core.smducar_router.select_row_mode_handler",
            return_value=None,
        ):
            result = CaseLawRouter.process_batch(
                router,
                frame,
                frame,
                "mapping.xlsx",
                progress,
                "main",
            )

        self.assertEqual((0, 0), result)
        router._mark_remaining_rows_after_router_session_loss.assert_called_once_with(
            frame,
            43,
            "browser gone",
        )
        self.assertEqual(
            [
                call("main", 0, 2),
                call("main", 1, 2),
                call("main", 2, 2),
            ],
            progress.call_args_list,
        )
        self.assertEqual(
            "ERROR: ROUTER SESSION LOST",
            error_log_entries[0]["Status"],
        )
        self.assertEqual(1, router.validate_row.call_count)


if __name__ == "__main__":
    unittest.main()
