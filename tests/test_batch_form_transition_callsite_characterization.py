"""Phase 8A characterization of the batch form-transition call site."""

import unittest
from types import SimpleNamespace
from unittest.mock import ANY, Mock, call

from core.smducar_config import (
    error_log_entries,
    mspb_metadata_buffer,
    status_updates_buffer,
)
from core.smducar_router import RouterSessionLostError
from tests.test_document_outcome_callsite_characterization import (
    _router,
    _run,
)


class BatchFormTransitionCallsiteCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()
        mspb_metadata_buffer.clear()
        error_log_entries.clear()

    def test_shared_search_precedes_form_open_with_exact_arguments(self):
        router = _router()
        timeline = Mock()
        timeline.attach_mock(router.handle_lni_search, "search")
        timeline.attach_mock(router.open_and_process_form, "open")

        result, frame, _, _, _ = _run(
            router,
            dar_mode=True,
            wc_mode=True,
        )

        self.assertEqual((1, 2), result)
        self.assertEqual("search", timeline.mock_calls[0][0])
        self.assertEqual("open", timeline.mock_calls[1][0])
        router.handle_lni_search.assert_called_once_with("LNI-1")
        args = router.open_and_process_form.call_args.args
        kwargs = router.open_and_process_form.call_args.kwargs
        self.assertEqual("LNI-1", args[0]["LNI"])
        self.assertIs(frame, args[1])
        self.assertEqual((7, "mapping.xlsx"), args[2:])
        self.assertEqual(
            {
                "dar_mode": True,
                "wc_mode": True,
                "mspb_mode": False,
                "mspb_metadata": None,
                "itc_metadata": None,
                "irsplr_metadata": None,
                "ohtax0_metadata": None,
                "mnsutb_metadata": None,
            },
            kwargs,
        )

    def test_shared_search_failure_sets_status_and_skips_form_retry(self):
        router = _router()
        router.handle_lni_search.return_value = False
        progress = Mock()

        result, _, _, _, _ = _run(router, progress=progress)

        self.assertEqual((0, 0), result)
        self.assertEqual("ERROR: LNI NOT FOUND", status_updates_buffer[7])
        router.open_and_process_form.assert_not_called()
        router._should_refresh_retry_form_status.assert_not_called()
        router._refresh_and_retry_current_row.assert_not_called()
        self.assertEqual(
            [call("main", 0, 1), call("main", 1, 1)],
            progress.call_args_list,
        )

    def test_document_path_skips_shared_search_and_forwards_exact_form_arguments(self):
        router = _router()
        metadata = object()
        router.process_mspb_document_row.return_value = SimpleNamespace(
            metadata=metadata,
            continue_to_form=True,
            row_status=None,
        )

        result, frame, _, _, _ = _run(
            router,
            batch_type="mspb",
            mspb_mode=True,
            dar_mode=True,
            wc_mode=True,
        )

        self.assertEqual((1, 2), result)
        router.handle_lni_search.assert_not_called()
        args = router.open_and_process_form.call_args.args
        kwargs = router.open_and_process_form.call_args.kwargs
        self.assertEqual("LNI-1", args[0]["LNI"])
        self.assertIs(frame, args[1])
        self.assertEqual((7, "mapping.xlsx"), args[2:])
        self.assertEqual(
            {
                "dar_mode": True,
                "wc_mode": True,
                "mspb_mode": True,
                "mspb_metadata": metadata,
                "itc_metadata": None,
                "irsplr_metadata": None,
                "ohtax0_metadata": None,
                "mnsutb_metadata": None,
            },
            kwargs,
        )

    def test_nonrecoverable_form_status_bypasses_refresh_retry(self):
        router = _router()
        router.open_and_process_form.return_value = "custom form status"
        router._should_refresh_retry_form_status.return_value = False
        status_updates_buffer[7] = "PROCESSING"

        result, _, _, _, _ = _run(router)

        self.assertEqual((1, 2), result)
        router._should_refresh_retry_form_status.assert_called_once_with(
            "custom form status",
            7,
        )
        router._refresh_and_retry_current_row.assert_not_called()
        self.assertEqual("CUSTOM FORM STATUS", status_updates_buffer[7])

    def test_recoverable_status_forwards_exact_retry_arguments(self):
        router = _router()
        metadata = object()
        router.process_mspb_document_row.return_value = SimpleNamespace(
            metadata=metadata,
            continue_to_form=True,
            row_status=None,
        )
        router.open_and_process_form.return_value = "RELATED LNI ERROR"
        router._should_refresh_retry_form_status.return_value = True
        router._refresh_and_retry_current_row.return_value = "DONE"

        result, frame, _, _, _ = _run(
            router,
            batch_type="mspb",
            mspb_mode=True,
            dar_mode=True,
            wc_mode=True,
        )

        self.assertEqual((1, 2), result)
        router._should_refresh_retry_form_status.assert_called_once_with(
            "RELATED LNI ERROR",
            7,
        )
        args = router._refresh_and_retry_current_row.call_args.args
        kwargs = router._refresh_and_retry_current_row.call_args.kwargs
        self.assertEqual("LNI-1", args[0]["LNI"])
        self.assertIs(frame, args[1])
        self.assertEqual(
            (7, "mapping.xlsx", "RELATED LNI ERROR"),
            args[2:],
        )
        self.assertEqual(
            {
                "dar_mode": True,
                "wc_mode": True,
                "mspb_mode": True,
                "mspb_metadata": metadata,
                "itc_metadata": None,
                "irsplr_metadata": None,
                "ohtax0_metadata": None,
                "mnsutb_metadata": None,
            },
            kwargs,
        )

    def test_retry_result_replaces_initial_status_before_finalization(self):
        router = _router()
        router.open_and_process_form.return_value = "RELATED LNI ERROR"
        router._should_refresh_retry_form_status.return_value = True
        router._refresh_and_retry_current_row.return_value = (
            "related lni timeout"
        )
        status_updates_buffer[7] = "PROCESSING"

        result, _, _, _, _ = _run(router)

        self.assertEqual((1, 2), result)
        self.assertEqual("RELATED LNI TIMEOUT", status_updates_buffer[7])

    def test_transition_failures_enter_generic_cleanup_and_finally(self):
        cases = (
            "shared_search",
            "form_open",
            "retry_decision",
            "retry_call",
        )

        for failure_point in cases:
            with self.subTest(failure_point=failure_point):
                status_updates_buffer.clear()
                router = _router()
                progress = Mock()
                recorder = Mock()
                original = RuntimeError(f"{failure_point} failed")
                if failure_point == "shared_search":
                    router.handle_lni_search.side_effect = original
                elif failure_point == "form_open":
                    router.open_and_process_form.side_effect = original
                elif failure_point == "retry_decision":
                    router._should_refresh_retry_form_status.side_effect = (
                        original
                    )
                else:
                    router._should_refresh_retry_form_status.return_value = (
                        True
                    )
                    router._refresh_and_retry_current_row.side_effect = (
                        original
                    )

                timeline = Mock()
                timeline.attach_mock(recorder, "record")
                timeline.attach_mock(router.driver.close, "close")
                timeline.attach_mock(
                    router.driver.switch_to.window,
                    "focus",
                )
                timeline.attach_mock(progress, "progress")

                result, _, _, _, patched_recorder = _run(
                    router,
                    progress=progress,
                    error_recorder=recorder,
                )

                self.assertEqual((0, 0), result)
                self.assertIs(original, patched_recorder.call_args.args[3])
                timeline.assert_has_calls(
                    [
                        call.record(
                            router,
                            7,
                            ANY,
                            original,
                            mspb_mode=False,
                            metadata_buffer=mspb_metadata_buffer,
                            status_buffer=status_updates_buffer,
                            error_entries=error_log_entries,
                            is_itc_row=ANY,
                            is_irsplr_row=ANY,
                            is_ohtax0_row=ANY,
                            is_mnsutb_row=ANY,
                        ),
                        call.close(),
                        call.focus("main"),
                        call.progress("main", 1, 1),
                    ]
                )

    def test_transition_session_loss_uses_stop_path_without_generic_cleanup(self):
        router = _router()
        original = RouterSessionLostError("browser gone")
        router.open_and_process_form.side_effect = original
        recorder = Mock()
        progress = Mock()

        result, _, _, _, patched_recorder = _run(
            router,
            progress=progress,
            error_recorder=recorder,
        )

        self.assertEqual((0, 0), result)
        patched_recorder.assert_not_called()
        router.driver.close.assert_not_called()
        router._mark_remaining_rows_after_router_session_loss.assert_called_once()
        self.assertEqual(
            [
                call("main", 0, 1),
                call("main", 1, 1),
                call("main", 1, 1),
            ],
            progress.call_args_list,
        )


if __name__ == "__main__":
    unittest.main()
