"""Characterization tests for router session-loss policy."""

import ast
import importlib.util
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch

import pandas as pd

from core.smducar_config import status_updates_buffer
from core.router_modes.session_loss_policy import (
    handle_batch_session_loss,
)
from core.smducar_router import CaseLawRouter, RouterSessionLostError


class _TrackingEntries(list):
    def __init__(self, events, *, error=None):
        super().__init__()
        self.events = events
        self.error = error

    def append(self, value):
        self.events.append("append")
        if self.error:
            raise self.error
        super().append(value)


class SessionLossPolicyCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_invalid_session_markers_remain_case_insensitive(self):
        markers = (
            "invalid session id",
            "chrome not reachable",
            "disconnected",
            "not connected to devtools",
            "target window already closed",
            "no such window",
        )
        for marker in markers:
            with self.subTest(marker=marker):
                self.assertTrue(
                    CaseLawRouter._is_invalid_session_error(
                        RuntimeError(f"PREFIX {marker.upper()} suffix")
                    )
                )

        for value in (None, RuntimeError("timeout"), "", "ordinary error"):
            with self.subTest(value=value):
                self.assertFalse(
                    CaseLawRouter._is_invalid_session_error(value)
                )

    def test_raise_helper_preserves_context_message_and_exception_chain(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        original = RuntimeError("invalid session id: gone")

        with self.assertRaisesRegex(
            RouterSessionLostError,
            "during opening form: invalid session id: gone",
        ) as raised:
            CaseLawRouter._raise_if_invalid_session_error(
                router,
                original,
                "opening form",
            )

        self.assertIs(original, raised.exception.__cause__)

    def test_raise_helper_returns_none_for_non_session_error(self):
        router = CaseLawRouter.__new__(CaseLawRouter)

        result = CaseLawRouter._raise_if_invalid_session_error(
            router,
            RuntimeError("ordinary timeout"),
        )

        self.assertIsNone(result)

    def test_remaining_rows_start_at_current_and_preserve_completed(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        frame = pd.DataFrame(
            {
                "Status": [
                    "",
                    "",
                    "",
                    " done ",
                    "",
                    "ALREADY PROCESSED",
                ]
            },
            index=[10, 20, 30, 40, 50, 60],
        )
        status_updates_buffer[50] = " already processed "

        result = CaseLawRouter._mark_remaining_rows_after_router_session_loss(
            router,
            frame,
            30,
            "browser gone",
        )

        self.assertIsNone(result)
        self.assertNotIn(10, status_updates_buffer)
        self.assertNotIn(20, status_updates_buffer)
        self.assertEqual(
            "NEEDS RERUN - INTERRUPTED",
            status_updates_buffer[30],
        )
        self.assertNotIn(40, status_updates_buffer)
        self.assertEqual(" already processed ", status_updates_buffer[50])
        self.assertNotIn(60, status_updates_buffer)

    def test_buffer_status_precedes_dataframe_status(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        frame = pd.DataFrame(
            {"Status": ["DONE", "ALREADY PROCESSED"]},
            index=[70, 80],
        )
        status_updates_buffer[70] = "PROCESSING"

        CaseLawRouter._mark_remaining_rows_after_router_session_loss(
            router,
            frame,
            70,
            "browser gone",
        )

        self.assertEqual(
            "NEEDS RERUN - INTERRUPTED",
            status_updates_buffer[70],
        )
        self.assertNotIn(80, status_updates_buffer)

    def test_missing_current_index_marks_nothing(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        frame = pd.DataFrame(
            {"Status": ["", ""]},
            index=[100, 110],
        )

        CaseLawRouter._mark_remaining_rows_after_router_session_loss(
            router,
            frame,
            999,
            "browser gone",
        )

        self.assertEqual({}, status_updates_buffer)

    def test_batch_outcome_preserves_log_mark_append_order_and_payload(self):
        events = []
        router = Mock()
        router._mark_remaining_rows_after_router_session_loss.side_effect = (
            lambda *args: events.append("mark")
        )
        frame = object()
        row = {"LNI": "LNI-LOST", "FileName": "lost.pdf"}
        error = RouterSessionLostError("browser gone")
        entries = _TrackingEntries(events)

        with patch(
            "core.router_modes.session_loss_policy.logging.error",
            side_effect=lambda *args, **kwargs: events.append("log"),
        ) as log:
            outcome = handle_batch_session_loss(
                router,
                frame,
                43,
                row,
                error,
                entries,
            )

        self.assertEqual(["log", "mark", "append"], events)
        log.assert_called_once_with(
            "Router session lost while processing row 45: browser gone"
        )
        router._mark_remaining_rows_after_router_session_loss.assert_called_once_with(
            frame,
            43,
            "browser gone",
        )
        self.assertEqual(
            [
                {
                    "Row": 45,
                    "LNI": "LNI-LOST",
                    "File Name": "lost.pdf",
                    "Status": "ERROR: ROUTER SESSION LOST",
                    "Error Message": "browser gone",
                }
            ],
            entries,
        )
        self.assertTrue(outcome.stop_batch)
        with self.assertRaises(FrozenInstanceError):
            outcome.stop_batch = False

    def test_batch_outcome_mark_failure_propagates_before_append(self):
        router = Mock()
        router._mark_remaining_rows_after_router_session_loss.side_effect = (
            RuntimeError("mark failed")
        )
        entries = []

        with self.assertRaisesRegex(RuntimeError, "mark failed"):
            handle_batch_session_loss(
                router,
                object(),
                5,
                {},
                RouterSessionLostError("browser gone"),
                entries,
            )

        self.assertEqual([], entries)

    def test_batch_outcome_append_failure_propagates_after_mark(self):
        router = Mock()
        entries = _TrackingEntries(
            [],
            error=RuntimeError("append failed"),
        )

        with self.assertRaisesRegex(RuntimeError, "append failed"):
            handle_batch_session_loss(
                router,
                object(),
                5,
                {},
                RouterSessionLostError("browser gone"),
                entries,
            )

        router._mark_remaining_rows_after_router_session_loss.assert_called_once()

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.session_loss_policy"),
        "structural boundary applies after extraction",
    )
    def test_router_methods_become_thin_compatibility_entry_points(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))

        for method_name in (
            "_is_invalid_session_error",
            "_raise_if_invalid_session_error",
            "_mark_remaining_rows_after_router_session_loss",
        ):
            with self.subTest(method_name=method_name):
                method = next(
                    node
                    for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef)
                    and node.name == method_name
                )
                executable_body = [
                    statement
                    for statement in method.body
                    if not (
                        isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Constant)
                        and isinstance(statement.value.value, str)
                    )
                ]
                self.assertEqual(1, len(executable_body))
                self.assertIsInstance(executable_body[0], ast.Return)

    @unittest.skipUnless(
        importlib.util.find_spec("core.router_modes.session_loss_policy"),
        "structural boundary applies after extraction",
    )
    def test_extracted_policy_remains_independent_of_browser_automation(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "session_loss_policy.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("invalid session id", source)
        self.assertIn("STATUS_NEEDS_RERUN_INTERRUPTED", source)
        for browser_term in (
            "selenium",
            "WebDriverWait",
            "window_handles",
            "driver.",
        ):
            with self.subTest(browser_term=browser_term):
                self.assertNotIn(browser_term, source)


if __name__ == "__main__":
    unittest.main()
