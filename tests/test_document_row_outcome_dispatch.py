"""Direct contracts for the Phase 7B document-row outcome dispatcher."""

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock


MODE_METHODS = {
    "mspb": "process_mspb_document_row",
    "itc": "process_itc_document_row",
    "irsplr": "process_irsplr_document_row",
    "ohtax0": "process_ohtax0_document_row",
    "mnsutb": "process_mnsutb_document_row",
}

MODE_SLOTS = {
    "mspb": "mspb_metadata",
    "itc": "itc_metadata",
    "irsplr": "irsplr_metadata",
    "ohtax0": "ohtax0_metadata",
    "mnsutb": "mnsutb_metadata",
}


def _dependencies(handler=None):
    return {
        "is_itc_row": Mock(return_value=True),
        "is_irsplr_row": Mock(return_value=True),
        "is_ohtax0_row": Mock(return_value=True),
        "is_mnsutb_row": Mock(return_value=True),
        "select_handler": Mock(return_value=handler),
    }


def _dispatch(router, row, dependencies, **flags):
    from core.router_modes.document_row_outcome_dispatch import (
        dispatch_document_row_outcome,
    )

    return dispatch_document_row_outcome(
        router,
        7,
        row,
        "LNI-1",
        mspb_mode=flags.get("mspb_mode", False),
        irsplr_mode=flags.get("irsplr_mode", False),
        ohtax0_mode=flags.get("ohtax0_mode", False),
        mnsutb_mode=flags.get("mnsutb_mode", False),
        **dependencies,
    )


class DocumentRowOutcomeDispatchTests(unittest.TestCase):
    def test_each_handler_invokes_exact_wrapper_and_metadata_slot(self):
        row = {"LNI": "LNI-1"}

        for mode, method_name in MODE_METHODS.items():
            with self.subTest(mode=mode):
                router = Mock()
                metadata = object()
                handler = Mock()
                handler.key = mode
                getattr(router, method_name).return_value = SimpleNamespace(
                    metadata=metadata,
                    continue_to_form=True,
                    row_status=None,
                )
                dependencies = _dependencies(handler)

                outcome = _dispatch(router, row, dependencies)

                getattr(router, method_name).assert_called_once_with(
                    handler,
                    7,
                    row,
                    "LNI-1",
                )
                self.assertTrue(outcome.handled_document)
                self.assertEqual(mode, outcome.handler_key)
                self.assertTrue(outcome.continue_to_form)
                self.assertIsNone(outcome.row_status)
                for key, slot in MODE_SLOTS.items():
                    self.assertIs(
                        metadata if key == mode else None,
                        getattr(outcome, slot),
                    )

    def test_eager_predicates_and_selector_arguments_are_preserved(self):
        router = Mock()
        handler = Mock()
        handler.key = "mspb"
        router.process_mspb_document_row.return_value = SimpleNamespace(
            metadata=object(),
            continue_to_form=False,
            row_status="MSPB STOP",
        )
        dependencies = _dependencies(handler)
        row = {"LNI": "LNI-1"}

        outcome = _dispatch(
            router,
            row,
            dependencies,
            mspb_mode=True,
            irsplr_mode=True,
            ohtax0_mode=True,
            mnsutb_mode=True,
        )

        for predicate_name in (
            "is_itc_row",
            "is_irsplr_row",
            "is_ohtax0_row",
            "is_mnsutb_row",
        ):
            dependencies[predicate_name].assert_called_once_with(row)
        dependencies["select_handler"].assert_called_once_with(
            mspb_mode=True,
            row_is_itc=True,
            irsplr_mode=True,
            row_is_irsplr=True,
            ohtax0_mode=True,
            row_is_ohtax0=True,
            mnsutb_mode=True,
            row_is_mnsutb=True,
        )
        self.assertFalse(outcome.continue_to_form)
        self.assertEqual("MSPB STOP", outcome.row_status)

    def test_no_handler_returns_shared_fallback_with_empty_slots(self):
        router = Mock()
        dependencies = _dependencies(None)

        outcome = _dispatch(router, {"LNI": "LNI-1"}, dependencies)

        self.assertFalse(outcome.handled_document)
        self.assertIsNone(outcome.handler_key)
        self.assertTrue(outcome.continue_to_form)
        self.assertIsNone(outcome.row_status)
        for slot in MODE_SLOTS.values():
            self.assertIsNone(getattr(outcome, slot))
        for method_name in MODE_METHODS.values():
            getattr(router, method_name).assert_not_called()

    def test_unknown_handler_preserves_shared_fallback_behavior(self):
        router = Mock()
        handler = Mock()
        handler.key = "unknown"
        dependencies = _dependencies(handler)

        outcome = _dispatch(router, {"LNI": "LNI-1"}, dependencies)

        self.assertFalse(outcome.handled_document)
        self.assertIsNone(outcome.handler_key)
        for method_name in MODE_METHODS.values():
            getattr(router, method_name).assert_not_called()

    def test_predicate_failure_propagates_before_selection(self):
        router = Mock()
        dependencies = _dependencies()
        original = RuntimeError("predicate failed")
        dependencies["is_itc_row"].side_effect = original

        with self.assertRaisesRegex(RuntimeError, "predicate failed") as raised:
            _dispatch(router, {"LNI": "LNI-1"}, dependencies)

        self.assertIs(original, raised.exception)
        dependencies["is_irsplr_row"].assert_not_called()
        dependencies["select_handler"].assert_not_called()

    def test_wrapper_failure_propagates_unchanged(self):
        router = Mock()
        handler = Mock()
        handler.key = "itc"
        original = RuntimeError("wrapper failed")
        router.process_itc_document_row.side_effect = original
        dependencies = _dependencies(handler)

        with self.assertRaisesRegex(RuntimeError, "wrapper failed") as raised:
            _dispatch(router, {"LNI": "LNI-1"}, dependencies)

        self.assertIs(original, raised.exception)

    def test_outcome_is_immutable(self):
        outcome = _dispatch(
            Mock(),
            {"LNI": "LNI-1"},
            _dependencies(None),
        )

        with self.assertRaises(FrozenInstanceError):
            outcome.handled_document = True

    def test_module_has_no_selenium_config_buffer_or_extractor_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "document_row_outcome_dispatch.py"
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
            "mspb_extractor",
            "itc_extractor",
            "irsplr_extractor",
            "ohtax0_extractor",
            "mnsutb_extractor",
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
        self.assertNotIn("driver.", source)


if __name__ == "__main__":
    unittest.main()
