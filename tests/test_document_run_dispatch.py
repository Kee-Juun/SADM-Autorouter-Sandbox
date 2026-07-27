"""No-driver contracts for Phase 6F document-only run dispatch."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

import pandas as pd
from pandas.testing import assert_frame_equal

from core.router_modes.document_run_dispatch import (
    dispatch_document_run,
)
from core.smducar_router import CaseLawRouter


def _frames():
    full = pd.DataFrame(
        [{"FileName": "document.pdf", "LNI": "LNI-1"}],
        index=[5],
    )
    counsel = full.iloc[0:0].copy()
    filtered_main = full.copy()
    return full, counsel, filtered_main


def _router(result=(2, 125)):
    router = Mock()
    router.set_status = Mock()
    router.process_batch.return_value = result
    return router


class DocumentRunDispatchTests(unittest.TestCase):
    def test_each_mode_preserves_dataframe_batch_flags_and_statuses(self):
        cases = (
            (
                "mspb",
                {"mspb_mode": True},
                {"mspb_mode": True},
                "MSPB Batch Started",
                "MSPB Batch Processed",
            ),
            (
                "itc",
                {"itc_mode": True},
                {},
                "ITC Batch Started",
                "ITC Batch Processed",
            ),
            (
                "irsplr",
                {"irsplr_mode": True},
                {"irsplr_mode": True},
                "IRSPLR Batch Started",
                "IRSPLR Batch Processed",
            ),
            (
                "ohtax0",
                {"ohtax0_mode": True},
                {"ohtax0_mode": True},
                "OHTAX0 Batch Started",
                "OHTAX0 Batch Processed",
            ),
            (
                "mnsutb",
                {"mnsutb_mode": True},
                {"mnsutb_mode": True},
                "MNSUTB Batch Started",
                "MNSUTB Batch Processed",
            ),
        )

        for key, flags, batch_kwargs, started, processed in cases:
            with self.subTest(mode=key):
                full, counsel, filtered_main = _frames()
                router = _router()

                outcome = dispatch_document_run(
                    router,
                    full,
                    counsel,
                    filtered_main,
                    "mapping.xlsx",
                    "progress",
                    dar_mode=True,
                    wc_mode=True,
                    **flags,
                )

                self.assertIsNotNone(outcome)
                self.assertEqual(key, outcome.mode_key)
                expected_batch_rows = (
                    filtered_main if key == "mspb" else full
                )
                batch_call = router.process_batch.call_args
                assert_frame_equal(batch_call.args[0], expected_batch_rows)
                self.assertIs(full, batch_call.args[1])
                self.assertEqual(
                    (
                        "mapping.xlsx",
                        "progress",
                        key,
                        True,
                        True,
                    ),
                    batch_call.args[2:],
                )
                self.assertEqual(batch_kwargs, batch_call.kwargs)
                self.assertEqual(
                    [call(started), call(processed)],
                    router.set_status.call_args_list,
                )
                if key == "mspb":
                    assert_frame_equal(outcome.counsel_df, counsel)
                    assert_frame_equal(
                        outcome.main_df,
                        filtered_main,
                    )
                else:
                    self.assertTrue(outcome.counsel_df.empty)
                    assert_frame_equal(outcome.main_df, full)

    def test_contradictory_flags_preserve_document_precedence(self):
        full, counsel, filtered_main = _frames()
        router = _router()

        outcome = dispatch_document_run(
            router,
            full,
            counsel,
            filtered_main,
            "mapping.xlsx",
            None,
            mspb_mode=True,
            itc_mode=True,
            irsplr_mode=True,
            ohtax0_mode=True,
            mnsutb_mode=True,
        )

        self.assertEqual("mspb", outcome.mode_key)
        self.assertEqual(
            {"mspb_mode": True},
            router.process_batch.call_args.kwargs,
        )

    def test_no_document_flag_returns_none_without_runtime_calls(self):
        full, counsel, filtered_main = _frames()
        router = _router()

        outcome = dispatch_document_run(
            router,
            full,
            counsel,
            filtered_main,
            "mapping.xlsx",
            None,
            dar_mode=True,
            wc_mode=True,
        )

        self.assertIsNone(outcome)
        router.process_batch.assert_not_called()
        router.set_status.assert_not_called()

    def test_zero_processed_rows_emits_no_summary(self):
        full, counsel, filtered_main = _frames()
        router = _router(result=(0, 125))

        with patch(
            "core.router_modes.document_run_dispatch.logging.info"
        ) as log:
            dispatch_document_run(
                router,
                full,
                counsel,
                filtered_main,
                "mapping.xlsx",
                None,
                itc_mode=True,
            )

        self.assertNotIn(
            "[ITC PROCESSING SUMMARY] ITC: %d LNIs processed in %dm %ds",
            [item.args[0] for item in log.call_args_list],
        )

    def test_batch_errors_propagate_to_process_rows_boundary(self):
        full, counsel, filtered_main = _frames()
        router = _router()
        router.process_batch.side_effect = RuntimeError("batch failed")

        with self.assertRaisesRegex(RuntimeError, "batch failed"):
            dispatch_document_run(
                router,
                full,
                counsel,
                filtered_main,
                "mapping.xlsx",
                None,
                itc_mode=True,
            )

        router.set_status.assert_called_once_with("ITC Batch Started")

    def test_router_method_is_a_thin_compatibility_wrapper(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        full, counsel, filtered_main = _frames()
        expected = object()

        with patch(
            "core.smducar_router.run_dispatch_document_run",
            return_value=expected,
        ) as delegated:
            actual = CaseLawRouter.dispatch_document_run(
                router,
                full,
                counsel,
                filtered_main,
                "mapping.xlsx",
                "progress",
                dar_mode=True,
                wc_mode=True,
                itc_mode=True,
            )

        self.assertIs(expected, actual)
        delegated.assert_called_once_with(
            router,
            full,
            counsel,
            filtered_main,
            "mapping.xlsx",
            "progress",
            dar_mode=True,
            wc_mode=True,
            mspb_mode=False,
            itc_mode=True,
            irsplr_mode=False,
            ohtax0_mode=False,
            mnsutb_mode=False,
        )

    def test_module_has_no_selenium_router_or_buffer_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "document_run_dispatch.py"
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
