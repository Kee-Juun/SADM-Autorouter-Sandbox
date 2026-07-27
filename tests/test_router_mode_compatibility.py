"""Contract tests for canonical mode and legacy-flag compatibility."""

import sys
import types
import unittest
from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

from core.router_modes import (
    LegacyModeFlags,
    flags_for_mode,
    mode_from_flags,
    normalize_mode,
    run_automation_for_mode,
)


EXPECTED_TRUE_FLAG = {
    "smd": None,
    "dar": "dar_mode",
    "mspb": "mspb_mode",
    "itc": "itc_mode",
    "irsplr": "irsplr_mode",
    "ohtax0": "ohtax0_mode",
    "mnsutb": "mnsutb_mode",
}


class RouterModeCompatibilityTests(unittest.TestCase):
    def test_each_mode_expands_to_exactly_its_legacy_flag(self):
        for mode, expected_true_flag in EXPECTED_TRUE_FLAG.items():
            with self.subTest(mode=mode):
                flag_values = flags_for_mode(mode).as_workflow_kwargs()
                true_flags = {
                    name for name, enabled in flag_values.items() if enabled
                }
                expected = (
                    {expected_true_flag} if expected_true_flag is not None else set()
                )
                self.assertEqual(expected, true_flags)

    def test_normalization_preserves_config_fallback_behavior(self):
        self.assertEqual("dar", normalize_mode(None, dar_mode=True))
        self.assertEqual("smd", normalize_mode(None, dar_mode=False))
        self.assertEqual("itc", normalize_mode(" ITC "))
        self.assertEqual("smd", normalize_mode(""))
        self.assertEqual("smd", normalize_mode("unknown"))

    def test_mode_from_flags_preserves_full_legacy_precedence(self):
        all_enabled = LegacyModeFlags(
            dar_mode=True,
            wc_mode=True,
            mspb_mode=True,
            itc_mode=True,
            irsplr_mode=True,
            ohtax0_mode=True,
            mnsutb_mode=True,
        )
        self.assertEqual("mspb", mode_from_flags(all_enabled))

        precedence_cases = [
            (LegacyModeFlags(itc_mode=True, dar_mode=True), "itc"),
            (LegacyModeFlags(irsplr_mode=True, ohtax0_mode=True), "irsplr"),
            (LegacyModeFlags(ohtax0_mode=True, mnsutb_mode=True), "ohtax0"),
            (LegacyModeFlags(mnsutb_mode=True, dar_mode=True), "mnsutb"),
            (LegacyModeFlags(dar_mode=True, wc_mode=True), "dar"),
            (LegacyModeFlags(wc_mode=True), "smd"),
            (LegacyModeFlags(), "smd"),
        ]
        for flags, expected in precedence_cases:
            with self.subTest(flags=flags):
                self.assertEqual(expected, mode_from_flags(flags))

    def test_legacy_flags_are_immutable_and_return_fresh_kwargs(self):
        flags = flags_for_mode("dar")

        with self.assertRaises(FrozenInstanceError):
            flags.dar_mode = False

        first = flags.as_workflow_kwargs()
        second = flags.as_workflow_kwargs()
        self.assertEqual(first, second)
        self.assertIsNot(first, second)

    def test_wrapper_delegates_to_unchanged_workflow_with_exact_flags(self):
        workflow = Mock(return_value=("counsel", "main"))
        fake_workflow_module = types.ModuleType("core.smducar_workflow")
        fake_workflow_module.run_automation_workflow = workflow
        dataframe = object()
        callback = object()

        with patch.dict(
            sys.modules,
            {"core.smducar_workflow": fake_workflow_module},
        ):
            result = run_automation_for_mode(
                "irsplr",
                df=dataframe,
                update_progress=callback,
            )

        self.assertEqual(("counsel", "main"), result)
        workflow.assert_called_once_with(
            df=dataframe,
            update_progress=callback,
            dar_mode=False,
            wc_mode=False,
            mspb_mode=False,
            itc_mode=False,
            irsplr_mode=True,
            ohtax0_mode=False,
            mnsutb_mode=False,
        )

    def test_wrapper_owns_legacy_flags_even_if_supplied_by_caller(self):
        workflow = Mock()
        fake_workflow_module = types.ModuleType("core.smducar_workflow")
        fake_workflow_module.run_automation_workflow = workflow

        with patch.dict(
            sys.modules,
            {"core.smducar_workflow": fake_workflow_module},
        ):
            run_automation_for_mode(
                "itc",
                dar_mode=True,
                itc_mode=False,
            )

        delegated = workflow.call_args.kwargs
        self.assertFalse(delegated["dar_mode"])
        self.assertTrue(delegated["itc_mode"])


if __name__ == "__main__":
    unittest.main()
