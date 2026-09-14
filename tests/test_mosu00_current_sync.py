"""Regression coverage for the September 2026 MOSU production sync."""

import unittest
from unittest.mock import Mock

import pandas as pd

from core.mosu00_extractor import (
    MOSU00_TABLE_SOURCE_DETAIL,
    is_mosu00_row,
    parse_mosu00_html_text,
)
from core.router_modes import flags_for_mode, get_mode_spec
from core.router_modes.handlers import (
    get_document_mode_handler,
    select_row_mode_handler,
)
from core.router_modes.mosu00_batch_row import process_mosu00_document_row
from core.router_modes.orchestration import select_run_scope


class Mosu00CurrentSyncTests(unittest.TestCase):
    def test_table_html_metadata_preserves_compliance_source_detail(self):
        metadata = parse_mosu00_html_text(
            """<html><body><h1>Minutes of September 3, 2026</h1>
            <table><tr><td>SC 10001</td><td>SC-10002</td></tr></table>
            </body></html>""",
            filename_hint="LDC_SMD_MinutesofSeptember32026.html",
        )

        self.assertIsNotNone(metadata)
        self.assertEqual("SC10001", metadata.docket_number)
        self.assertEqual(("SC10001", "SC10002"), metadata.child_dockets)
        self.assertEqual("09-03-2026", metadata.decision_date)
        self.assertEqual("Table-(5-day spec source)", metadata.source_detail)
        self.assertEqual(MOSU00_TABLE_SOURCE_DETAIL, metadata.source_detail)

    def test_registry_and_scope_treat_mosu_as_hybrid_mode(self):
        spec = get_mode_spec("mosu00")
        self.assertFalse(spec.document_only)
        self.assertEqual(("counsel", "mosu00"), __import__(
            "core.router_modes.orchestration", fromlist=["BATCH_TYPES"]
        ).BATCH_TYPES["mosu00"])

        rows = pd.DataFrame([
            {"FileName": "LDC_SMD_SC10001.pdf", "CourtCode": "MOSU00"},
            {"FileName": "unrelated.pdf", "CourtCode": "OTHER"},
        ])
        selection = select_run_scope(
            rows,
            flags_for_mode("mosu00"),
            {"mosu00": is_mosu00_row},
        )
        self.assertEqual([0], list(selection.rows.index))

    def test_table_row_selects_mosu_handler_only_in_mosu_mode(self):
        handler = select_row_mode_handler(
            mosu00_mode=True,
            row_is_mosu00_table=True,
        )
        self.assertIs(get_document_mode_handler("mosu00"), handler)
        self.assertIsNone(select_row_mode_handler(row_is_mosu00_table=True))

    def test_table_batch_wrapper_extracts_records_and_opens_result(self):
        router = Mock()
        router.search_lni.return_value = True
        router.check_result_available.return_value = True
        metadata = parse_mosu00_html_text(
            "Minutes of September 3, 2026\nSC10001\nSC10002"
        )
        router.extract_mosu00_metadata_from_search_result.return_value = metadata
        handler = get_document_mode_handler("mosu00")
        row = {"FileName": "LDC_SMD_MinutesofSeptember32026.html"}

        outcome = process_mosu00_document_row(
            router, handler, 4, row, "LNI-1", "mapping.xlsx"
        )

        self.assertTrue(outcome.continue_to_form)
        self.assertIs(metadata, outcome.metadata)
        router.extract_mosu00_metadata_from_search_result.assert_called_once_with(
            row, 4, file_path="mapping.xlsx"
        )
        router.click_matching_result.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
