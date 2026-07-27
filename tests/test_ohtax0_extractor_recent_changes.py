"""Regression coverage for recent OHTAX0 header parsing changes."""

import unittest

from core.ohtax0_extractor import (
    OHTAX0_COURT_CODE,
    find_ohtax0_title_hint,
    parse_ohtax0_document_text,
)


class Ohtax0ExtractorRecentChangesTests(unittest.TestCase):
    def test_long_case_number_block_reaches_title_and_collects_all_numbers(self):
        case_numbers = [f"2026-{number}" for number in range(1001, 1013)]
        text = "\n".join(
            [
                "OHIO BOARD OF TAX APPEALS",
                "CASE NO(S).",
                *case_numbers,
                "DECISION AND ORDER",
                "Entered July 20, 2026",
            ]
        )

        metadata = parse_ohtax0_document_text(text)

        self.assertIsNotNone(metadata)
        self.assertEqual(OHTAX0_COURT_CODE, metadata.court)
        self.assertEqual(case_numbers[0], metadata.docket_number)
        self.assertEqual(tuple(case_numbers[1:]), metadata.other_numbers)
        self.assertEqual("DECISION AND ORDER", metadata.title_hint)
        self.assertEqual("Opinion", metadata.source_detail)
        self.assertEqual("07-20-2026", metadata.decision_date)

    def test_title_scan_stops_at_appearances_boundary(self):
        text = "\n".join(
            [
                "CASE NO(S).",
                "2026-1001",
                "APPEARANCES",
                "ORDER",
                "Entered July 20, 2026",
            ]
        )

        self.assertEqual("", find_ohtax0_title_hint(text))


if __name__ == "__main__":
    unittest.main()
