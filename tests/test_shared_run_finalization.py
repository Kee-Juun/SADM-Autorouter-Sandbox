"""No-driver contracts for the Phase 6G shared-run finalization slice."""

import ast
import datetime
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pandas as pd

from core.smducar_router import CaseLawRouter


class _FixedDatetime(datetime.datetime):
    values = []

    @classmethod
    def now(cls, tz=None):
        return cls.values.pop(0)


def _router(*, with_status=True):
    router = Mock()
    router.set_status = Mock() if with_status else None
    return router


class SharedRunFinalizationTests(unittest.TestCase):
    def test_sets_success_state_message_and_status_without_error_report(self):
        from core.router_modes.shared_run_finalization import (
            finalize_shared_run,
        )

        router = _router()
        success_time = datetime.datetime(2026, 7, 25, 12, 1, 2)
        _FixedDatetime.values = [success_time]

        with (
            patch(
                "core.router_modes.shared_run_finalization.datetime.datetime",
                _FixedDatetime,
            ),
            patch(
                "core.router_modes.shared_run_finalization.logging.info"
            ) as log,
            patch(
                "core.router_modes.shared_run_finalization.Path.home"
            ) as home,
            patch("pandas.DataFrame.to_excel") as to_excel,
        ):
            result = finalize_shared_run(router, [])

        self.assertIsNone(result)
        self.assertEqual(success_time, router._last_success_log_time)
        self.assertFalse(router._success_message_dismissed)
        router.set_status.assert_called_once_with("Success!")
        log.assert_called_once_with("Documents Auto-Routed Successfully!")
        home.assert_not_called()
        to_excel.assert_not_called()

    def test_omits_status_callback_when_router_has_none(self):
        from core.router_modes.shared_run_finalization import (
            finalize_shared_run,
        )

        router = _router(with_status=False)
        _FixedDatetime.values = [
            datetime.datetime(2026, 7, 25, 12, 1, 2)
        ]

        with patch(
            "core.router_modes.shared_run_finalization.datetime.datetime",
            _FixedDatetime,
        ):
            finalize_shared_run(router, [])

        self.assertFalse(router._success_message_dismissed)

    def test_writes_existing_error_entries_to_legacy_report_path(self):
        from core.router_modes.shared_run_finalization import (
            finalize_shared_run,
        )

        router = _router()
        entries = [{"Row": 7, "Status": "ERROR"}]
        virtual_home = Path("virtual-home")
        success_time = datetime.datetime(2026, 7, 25, 12, 1, 2)
        report_time = datetime.datetime(2026, 7, 25, 13, 2, 3)
        _FixedDatetime.values = [success_time, report_time]
        report_frame = Mock()

        with (
            patch(
                "core.router_modes.shared_run_finalization.datetime.datetime",
                _FixedDatetime,
            ),
            patch(
                "core.router_modes.shared_run_finalization.Path.home",
                return_value=virtual_home,
            ),
            patch.object(Path, "mkdir") as mkdir,
            patch(
                "core.router_modes.shared_run_finalization.pd.DataFrame",
                return_value=report_frame,
            ) as dataframe,
            patch(
                "core.router_modes.shared_run_finalization.logging.info"
            ) as log,
        ):
            finalize_shared_run(router, entries)

        expected_folder = (
            virtual_home
            / "Downloads"
            / "Case Law Auto-Routing Resources"
            / "Error Reports"
        )
        expected_path = expected_folder / "Error Report - 1-02-03_PM.xlsx"
        dataframe.assert_called_once_with(entries)
        mkdir.assert_called_once_with(parents=True, exist_ok=True)
        report_frame.to_excel.assert_called_once_with(
            expected_path,
            index=False,
        )
        self.assertEqual(
            [
                call("Documents Auto-Routed Successfully!"),
                call(f"Error report saved to {expected_path}"),
            ],
            log.call_args_list,
        )

    def test_report_write_error_propagates_after_success_state(self):
        from core.router_modes.shared_run_finalization import (
            finalize_shared_run,
        )

        router = _router()
        _FixedDatetime.values = [
            datetime.datetime(2026, 7, 25, 12, 1, 2),
            datetime.datetime(2026, 7, 25, 13, 2, 3),
        ]

        with (
            patch(
                "core.router_modes.shared_run_finalization.datetime.datetime",
                _FixedDatetime,
            ),
            patch(
                "core.router_modes.shared_run_finalization.Path.home",
                return_value=Path("virtual-home"),
            ),
            patch.object(Path, "mkdir"),
            patch(
                "pandas.DataFrame.to_excel",
                side_effect=OSError("write failed"),
            ),
            self.assertRaisesRegex(OSError, "write failed"),
        ):
            finalize_shared_run(router, [{"Status": "ERROR"}])

        router.set_status.assert_called_once_with("Success!")
        self.assertFalse(router._success_message_dismissed)

    def test_router_method_is_a_thin_compatibility_wrapper(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        expected = object()

        with patch(
            "core.smducar_router.run_finalize_shared_run",
            return_value=expected,
        ) as delegated:
            actual = CaseLawRouter.finalize_shared_run(router)

        self.assertIs(expected, actual)
        delegated.assert_called_once()
        self.assertIs(router, delegated.call_args.args[0])
        self.assertIs(
            delegated.call_args.args[1],
            __import__(
                "core.smducar_config",
                fromlist=["error_log_entries"],
            ).error_log_entries,
        )

    def test_process_rows_retains_finalization_failure_boundary(self):
        router = _router()
        full = pd.DataFrame([{"LNI": "LNI-1"}])
        counsel = full.iloc[0:0].copy()
        main = full.copy()
        router.dispatch_document_run.return_value = None
        router.dispatch_shared_run.return_value = SimpleNamespace(
            counsel_df=counsel,
            main_df=main,
        )
        router.finalize_shared_run.side_effect = OSError("write failed")

        with patch(
            "core.smducar_router.filter_mapping_data",
            return_value=(counsel, main),
        ):
            returned_counsel, returned_main = CaseLawRouter.process_rows(
                router,
                full,
                "mapping.xlsx",
                None,
            )

        router.finalize_shared_run.assert_called_once_with()
        self.assertTrue(returned_counsel.empty)
        self.assertTrue(returned_main.empty)

    def test_module_has_no_selenium_router_config_or_buffer_imports(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "shared_run_finalization.py"
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
        self.assertNotIn("mspb_metadata_buffer", source)
        self.assertNotIn("error_log_entries", source)


if __name__ == "__main__":
    unittest.main()
