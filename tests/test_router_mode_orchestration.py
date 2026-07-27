"""Characterization tests for extracted non-browser mode policy."""

import ast
import unittest
from pathlib import Path

import pandas as pd

from core.itc_extractor import is_itc_row
from core.irsplr_extractor import is_irsplr_row
from core.mnsutb_extractor import is_mnsutb_row
from core.ohtax0_extractor import is_ohtax0_row
from core.router_modes import LegacyModeFlags
from core.router_modes.orchestration import (
    EMPTY_SCOPE_MESSAGES,
    get_mode_run_plan,
    run_plan_from_flags,
    scope_key_from_flags,
    select_run_scope,
)


ROW_PREDICATES = {
    "itc": is_itc_row,
    "irsplr": is_irsplr_row,
    "ohtax0": is_ohtax0_row,
    "mnsutb": is_mnsutb_row,
}


class RouterModeOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.rows = pd.DataFrame(
            [
                {
                    "FileName": "itc000_337-1447_20260101.pdf",
                    "CourtCode": "FDITC000",
                },
                {
                    "FileName": "24-1234_opinion.pdf",
                    "CourtCode": "FDIRSPLR",
                },
                {
                    "FileName": "saq123_2026_1.pdf",
                    "CourtCode": "STOHTAX0",
                },
                {
                    "FileName": "LDC_SMD_A24-12345.pdf",
                    "CourtCode": "STMNSUTB",
                },
                {
                    "FileName": "LDC_SMD_24-9999.pdf",
                    "CourtCode": "USAP0001",
                },
            ],
            index=[10, 20, 30, 40, 50],
        )

    def test_run_plans_preserve_labels_batches_and_initial_statuses(self):
        expected = {
            "smd": ("SADM", False, ("counsel", "main"), "Counsel Batch Started"),
            "dar": ("DAR", False, ("counsel", "main"), "Counsel Batch Started"),
            "mspb": ("MSPB", True, ("mspb",), "MSPB Batch Started"),
            "itc": ("ITC", True, ("itc",), "ITC Batch Started"),
            "irsplr": ("IRSPLR", True, ("irsplr",), "IRSPLR Batch Started"),
            "ohtax0": ("OHTAX0", True, ("ohtax0",), "OHTAX0 Batch Started"),
            "mnsutb": ("MNSUTB", True, ("mnsutb",), "MNSUTB Batch Started"),
        }

        for mode, contract in expected.items():
            with self.subTest(mode=mode):
                plan = get_mode_run_plan(mode)
                self.assertEqual(contract, (
                    plan.router_label,
                    plan.document_only,
                    plan.batch_types,
                    plan.initial_status,
                ))

    def test_scope_selection_preserves_exact_row_indices_for_each_mode(self):
        cases = [
            (LegacyModeFlags(), [10, 20, 30, 40, 50]),
            (LegacyModeFlags(dar_mode=True), [10, 20, 30, 40, 50]),
            (LegacyModeFlags(mspb_mode=True), [10, 20, 30, 40, 50]),
            (LegacyModeFlags(itc_mode=True), [10]),
            (LegacyModeFlags(irsplr_mode=True), [20]),
            (LegacyModeFlags(ohtax0_mode=True), [30]),
            (LegacyModeFlags(mnsutb_mode=True), [40]),
        ]

        for flags, expected_indices in cases:
            with self.subTest(flags=flags):
                selection = select_run_scope(
                    self.rows,
                    flags,
                    ROW_PREDICATES,
                )
                self.assertEqual(expected_indices, list(selection.rows.index))

    def test_unrestricted_scope_preserves_original_dataframe_object(self):
        for flags in (
            LegacyModeFlags(),
            LegacyModeFlags(dar_mode=True),
            LegacyModeFlags(mspb_mode=True),
        ):
            with self.subTest(flags=flags):
                selection = select_run_scope(
                    self.rows,
                    flags,
                    ROW_PREDICATES,
                )
                self.assertIs(self.rows, selection.rows)

    def test_scope_precedence_remains_distinct_from_mode_precedence(self):
        flags = LegacyModeFlags(
            mspb_mode=True,
            itc_mode=True,
            irsplr_mode=True,
        )

        self.assertEqual("mspb", run_plan_from_flags(flags).mode_key)
        self.assertEqual("itc", scope_key_from_flags(flags))
        selection = select_run_scope(self.rows, flags, ROW_PREDICATES)
        self.assertEqual([10], list(selection.rows.index))

    def test_empty_scope_messages_match_existing_user_visible_contract(self):
        no_matches = self.rows.iloc[0:0].copy()
        cases = [
            (LegacyModeFlags(itc_mode=True), "itc"),
            (LegacyModeFlags(irsplr_mode=True), "irsplr"),
            (LegacyModeFlags(ohtax0_mode=True), "ohtax0"),
            (LegacyModeFlags(mnsutb_mode=True), "mnsutb"),
        ]

        for flags, scope_key in cases:
            with self.subTest(scope_key=scope_key):
                selection = select_run_scope(
                    no_matches,
                    flags,
                    ROW_PREDICATES,
                )
                self.assertEqual(
                    EMPTY_SCOPE_MESSAGES[scope_key],
                    selection.empty_scope_message,
                )

    def test_policy_module_has_no_workflow_router_or_selenium_imports(self):
        policy_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "orchestration.py"
        )
        tree = ast.parse(policy_path.read_text(encoding="utf-8"))
        imported_roots = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

        self.assertTrue(
            imported_roots.isdisjoint(
                {
                    "pandas",
                    "selenium",
                    "smducar_workflow",
                    "smducar_router",
                }
            ),
            imported_roots,
        )


if __name__ == "__main__":
    unittest.main()
