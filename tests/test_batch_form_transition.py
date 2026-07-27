"""Direct contracts for the Phase 8B batch form-transition wrapper."""

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call


METADATA_SLOTS = (
    "mspb_metadata",
    "itc_metadata",
    "irsplr_metadata",
    "ohtax0_metadata",
    "mnsutb_metadata",
)


def _document_outcome(*, handled_document=False, **metadata):
    values = {slot: None for slot in METADATA_SLOTS}
    values.update(metadata)
    return SimpleNamespace(
        handled_document=handled_document,
        **values,
    )


def _router():
    router = Mock()
    router.handle_lni_search.return_value = True
    router.open_and_process_form.return_value = "DONE"
    router._should_refresh_retry_form_status.return_value = False
    return router


def _transition(router, document_outcome=None, **flags):
    from core.router_modes.batch_form_transition import (
        process_batch_form_transition,
    )

    return process_batch_form_transition(
        router,
        {"LNI": "LNI-1"},
        "FULL_DF",
        7,
        "mapping.xlsx",
        "LNI-1",
        document_outcome or _document_outcome(),
        dar_mode=flags.get("dar_mode", False),
        wc_mode=flags.get("wc_mode", False),
        mspb_mode=flags.get("mspb_mode", False),
    )


class BatchFormTransitionTests(unittest.TestCase):
    def test_shared_search_precedes_form_open_with_exact_arguments(self):
        router = _router()
        timeline = Mock()
        timeline.attach_mock(router.handle_lni_search, "search")
        timeline.attach_mock(router.open_and_process_form, "open")

        outcome = _transition(router, dar_mode=True, wc_mode=True)

        self.assertEqual(["search", "open"], [c[0] for c in timeline.mock_calls])
        router.handle_lni_search.assert_called_once_with("LNI-1")
        router.open_and_process_form.assert_called_once_with(
            {"LNI": "LNI-1"},
            "FULL_DF",
            7,
            "mapping.xlsx",
            dar_mode=True,
            wc_mode=True,
            mspb_mode=False,
            mspb_metadata=None,
            itc_metadata=None,
            irsplr_metadata=None,
            ohtax0_metadata=None,
            mnsutb_metadata=None,
        )
        self.assertTrue(outcome.continue_to_finalization)
        self.assertEqual("DONE", outcome.form_status)
        self.assertIsNone(outcome.row_status)

    def test_shared_search_failure_returns_early_status_and_skips_form(self):
        router = _router()
        router.handle_lni_search.return_value = False

        outcome = _transition(router)

        self.assertFalse(outcome.continue_to_finalization)
        self.assertIsNone(outcome.form_status)
        self.assertEqual("ERROR: LNI NOT FOUND", outcome.row_status)
        router.open_and_process_form.assert_not_called()
        router._should_refresh_retry_form_status.assert_not_called()
        router._refresh_and_retry_current_row.assert_not_called()

    def test_document_path_skips_shared_search_and_forwards_metadata(self):
        router = _router()
        metadata = object()
        document_outcome = _document_outcome(
            handled_document=True,
            mspb_metadata=metadata,
        )

        outcome = _transition(
            router,
            document_outcome,
            dar_mode=True,
            wc_mode=True,
            mspb_mode=True,
        )

        router.handle_lni_search.assert_not_called()
        router.open_and_process_form.assert_called_once_with(
            {"LNI": "LNI-1"},
            "FULL_DF",
            7,
            "mapping.xlsx",
            dar_mode=True,
            wc_mode=True,
            mspb_mode=True,
            mspb_metadata=metadata,
            itc_metadata=None,
            irsplr_metadata=None,
            ohtax0_metadata=None,
            mnsutb_metadata=None,
        )
        self.assertTrue(outcome.continue_to_finalization)

    def test_nonrecoverable_status_bypasses_retry(self):
        router = _router()
        router.open_and_process_form.return_value = "CUSTOM"

        outcome = _transition(router)

        router._should_refresh_retry_form_status.assert_called_once_with(
            "CUSTOM",
            7,
        )
        router._refresh_and_retry_current_row.assert_not_called()
        self.assertEqual("CUSTOM", outcome.form_status)

    def test_recoverable_status_forwards_exact_retry_arguments(self):
        router = _router()
        metadata = object()
        document_outcome = _document_outcome(
            handled_document=True,
            itc_metadata=metadata,
        )
        router.open_and_process_form.return_value = "RECOVERABLE"
        router._should_refresh_retry_form_status.return_value = True
        router._refresh_and_retry_current_row.return_value = "DONE"

        _transition(
            router,
            document_outcome,
            dar_mode=True,
            wc_mode=True,
        )

        router._refresh_and_retry_current_row.assert_called_once_with(
            {"LNI": "LNI-1"},
            "FULL_DF",
            7,
            "mapping.xlsx",
            "RECOVERABLE",
            dar_mode=True,
            wc_mode=True,
            mspb_mode=False,
            mspb_metadata=None,
            itc_metadata=metadata,
            irsplr_metadata=None,
            ohtax0_metadata=None,
            mnsutb_metadata=None,
        )

    def test_retry_result_replaces_initial_form_status(self):
        router = _router()
        router.open_and_process_form.return_value = "INITIAL"
        router._should_refresh_retry_form_status.return_value = True
        router._refresh_and_retry_current_row.return_value = "RETRIED"

        outcome = _transition(router)

        self.assertEqual("RETRIED", outcome.form_status)

    def test_transition_failures_propagate_unchanged(self):
        cases = (
            "handle_lni_search",
            "open_and_process_form",
            "_should_refresh_retry_form_status",
            "_refresh_and_retry_current_row",
        )

        for method_name in cases:
            with self.subTest(method_name=method_name):
                router = _router()
                original = RuntimeError(f"{method_name} failed")
                if method_name == "_refresh_and_retry_current_row":
                    router._should_refresh_retry_form_status.return_value = (
                        True
                    )
                getattr(router, method_name).side_effect = original

                with self.assertRaisesRegex(
                    RuntimeError,
                    f"{method_name} failed",
                ) as raised:
                    _transition(router)

                self.assertIs(original, raised.exception)

    def test_outcome_is_immutable(self):
        outcome = _transition(_router())

        with self.assertRaises(FrozenInstanceError):
            outcome.form_status = "CHANGED"

    def test_module_has_no_selenium_config_buffer_or_driver_access(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "batch_form_transition.py"
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
        self.assertNotIn("driver.", source)


if __name__ == "__main__":
    unittest.main()
