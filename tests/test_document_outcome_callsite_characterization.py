"""Phase 7A characterization of process_batch document outcomes."""

import unittest
from contextlib import ExitStack
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pandas as pd

from core.smducar_config import (
    error_log_entries,
    mspb_metadata_buffer,
    status_updates_buffer,
)
from core.smducar_router import CaseLawRouter


MODE_METHODS = {
    "mspb": "process_mspb_document_row",
    "itc": "process_itc_document_row",
    "irsplr": "process_irsplr_document_row",
    "ohtax0": "process_ohtax0_document_row",
    "mnsutb": "process_mnsutb_document_row",
}

MODE_METADATA_SLOTS = {
    "mspb": "mspb_metadata",
    "itc": "itc_metadata",
    "irsplr": "irsplr_metadata",
    "ohtax0": "ohtax0_metadata",
    "mnsutb": "mnsutb_metadata",
}

PREDICATE_PATCHES = {
    "itc": "core.smducar_router.is_itc_row",
    "irsplr": "core.smducar_router.is_irsplr_row",
    "ohtax0": "core.smducar_router.is_ohtax0_row",
    "mnsutb": "core.smducar_router.is_mnsutb_row",
}


def _frame():
    return pd.DataFrame(
        [
            {
                "FileName": "document.pdf",
                "CourtCode": "",
                "LNI": "LNI-1",
                "Status": "",
            }
        ],
        index=[7],
    )


def _router():
    router = CaseLawRouter.__new__(CaseLawRouter)
    router.driver = Mock()
    router.driver.window_handles = ["main"]
    router.safe_alert_accept = Mock()
    router.validate_row = Mock(return_value="LNI-1")
    router.handle_lni_search = Mock(return_value=True)
    router.open_and_process_form = Mock(return_value="DONE")
    router._should_refresh_retry_form_status = Mock(return_value=False)
    router._refresh_and_retry_current_row = Mock()
    router._mark_remaining_rows_after_router_session_loss = Mock()
    router.record_mspb_metadata = Mock()
    router.record_itc_metadata = Mock()
    router.record_irsplr_metadata = Mock()
    router.record_ohtax0_metadata = Mock()
    router.record_mnsutb_metadata = Mock()
    for method_name in MODE_METHODS.values():
        setattr(router, method_name, Mock())
    return router


def _flags(mode=None):
    return {
        "mspb_mode": mode == "mspb",
        "irsplr_mode": mode == "irsplr",
        "ohtax0_mode": mode == "ohtax0",
        "mnsutb_mode": mode == "mnsutb",
    }


def _run(
    router,
    *,
    batch_type="main",
    predicate_values=None,
    progress=None,
    error_recorder=None,
    **flags,
):
    frame = _frame()
    predicate_values = predicate_values or {}

    with ExitStack() as stack:
        predicates = {}
        for key, target in PREDICATE_PATCHES.items():
            value = predicate_values.get(key, False)
            predicate = (
                Mock(side_effect=value)
                if isinstance(value, BaseException)
                else Mock(return_value=value)
            )
            predicates[key] = stack.enter_context(
                patch(target, predicate)
            )
        stack.enter_context(
            patch(
                "core.smducar_router.time.time",
                side_effect=[0, 10, 12, 15],
            )
        )
        mark = stack.enter_context(
            patch("core.smducar_router.mark_row_processing")
        )
        recorder = None
        if error_recorder is not None:
            recorder = stack.enter_context(
                patch(
                    "core.smducar_router.record_batch_row_error",
                    error_recorder,
                )
            )

        result = CaseLawRouter.process_batch(
            router,
            frame,
            frame,
            "mapping.xlsx",
            progress,
            batch_type,
            **flags,
        )

    return result, frame, predicates, mark, recorder


class DocumentOutcomeCallsiteCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()
        mspb_metadata_buffer.clear()
        error_log_entries.clear()

    def test_each_document_outcome_populates_only_its_form_metadata_slot(self):
        for mode, method_name in MODE_METHODS.items():
            with self.subTest(mode=mode):
                status_updates_buffer.clear()
                router = _router()
                metadata = object()
                getattr(router, method_name).return_value = SimpleNamespace(
                    metadata=metadata,
                    continue_to_form=True,
                    row_status=None,
                )
                predicate_values = {"itc": mode == "itc"}

                result, frame, predicates, mark, _ = _run(
                    router,
                    batch_type=mode,
                    predicate_values=predicate_values,
                    **_flags(mode),
                )

                self.assertEqual((1, 2), result)
                wrapper = getattr(router, method_name)
                wrapper.assert_called_once()
                self.assertEqual(mode, wrapper.call_args.args[0].key)
                self.assertEqual(7, wrapper.call_args.args[1])
                self.assertEqual(
                    "LNI-1",
                    wrapper.call_args.args[2]["LNI"],
                )
                router.handle_lni_search.assert_not_called()
                kwargs = router.open_and_process_form.call_args.kwargs
                for key, slot in MODE_METADATA_SLOTS.items():
                    self.assertIs(
                        metadata if key == mode else None,
                        kwargs[slot],
                    )
                mark.assert_called_once_with(7)
                for predicate in predicates.values():
                    predicate.assert_called_once()

    def test_each_noncontinuing_outcome_writes_status_and_skips_form(self):
        for mode, method_name in MODE_METHODS.items():
            with self.subTest(mode=mode):
                status_updates_buffer.clear()
                router = _router()
                progress = Mock()
                expected_status = f"SKIPPED: {mode.upper()}"
                getattr(router, method_name).return_value = SimpleNamespace(
                    metadata=object(),
                    continue_to_form=False,
                    row_status=expected_status,
                )

                result, _, _, _, _ = _run(
                    router,
                    batch_type=mode,
                    predicate_values={"itc": mode == "itc"},
                    progress=progress,
                    **_flags(mode),
                )

                self.assertEqual((0, 0), result)
                self.assertEqual(expected_status, status_updates_buffer[7])
                router.open_and_process_form.assert_not_called()
                router.handle_lni_search.assert_not_called()
                self.assertEqual(
                    [call(mode, 0, 1), call(mode, 1, 1)],
                    progress.call_args_list,
                )

    def test_mspb_wins_when_all_flags_and_predicates_are_true(self):
        router = _router()
        router.process_mspb_document_row.return_value = SimpleNamespace(
            metadata=object(),
            continue_to_form=False,
            row_status="MSPB STOP",
        )

        _, _, predicates, _, _ = _run(
            router,
            batch_type="mspb",
            predicate_values={
                "itc": True,
                "irsplr": True,
                "ohtax0": True,
                "mnsutb": True,
            },
            mspb_mode=True,
            irsplr_mode=True,
            ohtax0_mode=True,
            mnsutb_mode=True,
        )

        router.process_mspb_document_row.assert_called_once()
        for key, method_name in MODE_METHODS.items():
            if key != "mspb":
                getattr(router, method_name).assert_not_called()
        for predicate in predicates.values():
            predicate.assert_called_once()

    def test_itc_wins_all_row_signals_without_mspb(self):
        router = _router()
        router.process_itc_document_row.return_value = SimpleNamespace(
            metadata=object(),
            continue_to_form=False,
            row_status="ITC STOP",
        )

        _run(
            router,
            batch_type="itc",
            predicate_values={
                "itc": True,
                "irsplr": True,
                "ohtax0": True,
                "mnsutb": True,
            },
            irsplr_mode=True,
            ohtax0_mode=True,
            mnsutb_mode=True,
        )

        router.process_itc_document_row.assert_called_once()
        router.process_irsplr_document_row.assert_not_called()
        router.process_ohtax0_document_row.assert_not_called()
        router.process_mnsutb_document_row.assert_not_called()

    def test_shared_search_runs_only_when_no_document_handler_exists(self):
        router = _router()

        result, _, _, _, _ = _run(router)

        self.assertEqual((1, 2), result)
        router.handle_lni_search.assert_called_once_with("LNI-1")
        router.open_and_process_form.assert_called_once()
        for method_name in MODE_METHODS.values():
            getattr(router, method_name).assert_not_called()
        for slot in MODE_METADATA_SLOTS.values():
            self.assertIsNone(
                router.open_and_process_form.call_args.kwargs[slot]
            )

    def test_shared_search_failure_sets_status_and_skips_form(self):
        router = _router()
        router.handle_lni_search.return_value = False
        progress = Mock()

        result, _, _, _, _ = _run(
            router,
            progress=progress,
        )

        self.assertEqual((0, 0), result)
        self.assertEqual(
            "ERROR: LNI NOT FOUND",
            status_updates_buffer[7],
        )
        router.open_and_process_form.assert_not_called()
        self.assertEqual(
            [call("main", 0, 1), call("main", 1, 1)],
            progress.call_args_list,
        )

    def test_wrapper_failure_enters_generic_recording_then_driver_cleanup(self):
        router = _router()
        original = RuntimeError("wrapper failed")
        router.process_mspb_document_row.side_effect = original
        recorder = Mock()
        progress = Mock()

        result, _, _, _, patched_recorder = _run(
            router,
            batch_type="mspb",
            progress=progress,
            error_recorder=recorder,
            mspb_mode=True,
        )

        self.assertEqual((0, 0), result)
        self.assertIs(
            original,
            patched_recorder.call_args.args[3],
        )
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")
        self.assertEqual(
            [call("mspb", 0, 1), call("mspb", 1, 1)],
            progress.call_args_list,
        )

    def test_predicate_failure_enters_generic_recording_then_driver_cleanup(self):
        router = _router()
        original = RuntimeError("predicate failed")
        recorder = Mock()
        progress = Mock()

        result, _, predicates, _, patched_recorder = _run(
            router,
            progress=progress,
            predicate_values={"itc": original},
            error_recorder=recorder,
        )

        self.assertEqual((0, 0), result)
        self.assertIs(
            original,
            patched_recorder.call_args.args[3],
        )
        predicates["irsplr"].assert_not_called()
        predicates["ohtax0"].assert_not_called()
        predicates["mnsutb"].assert_not_called()
        router.driver.close.assert_called_once_with()
        router.driver.switch_to.window.assert_called_once_with("main")
        self.assertEqual(
            [call("main", 0, 1), call("main", 1, 1)],
            progress.call_args_list,
        )


if __name__ == "__main__":
    unittest.main()
