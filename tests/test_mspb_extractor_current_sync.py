"""Offline regression coverage for the current MSPB title classification."""

import unittest

from core.mspb_extractor import (
    _line_is_mspb_title,
    classify_mspb_source_detail,
    parse_mspb_document_text,
)


class MSPBExtractorCurrentSyncTests(unittest.TestCase):
    def test_title_hint_with_trailing_text_classifies_final_order(self):
        text = """
        UNITED STATES OF AMERICA
        MERIT SYSTEMS PROTECTION BOARD
        DOCKET NUMBER
        DC-0752-24-0001-I-1
        DATE: July 29, 2026
        FINAL ORDER DISMISSING THE PETITION
        The petition is dismissed.
        """

        metadata = parse_mspb_document_text(text)

        self.assertIsNotNone(metadata)
        self.assertEqual("FINAL ORDER DISMISSING THE PETITION", metadata.title_hint)
        self.assertEqual("Order", metadata.source_detail)

    def test_decision_title_takes_precedence_over_order_elsewhere_in_header(self):
        result = classify_mspb_source_detail(
            "FDMSPB02",
            "MERIT SYSTEMS PROTECTION BOARD ORDER OF THE BOARD",
            title_hint="DECISION GRANTING CORRECTIVE ACTION",
        )

        self.assertEqual("Opinion", result)

    def test_title_recognizer_accepts_trailing_title_text(self):
        self.assertTrue(_line_is_mspb_title("OPINION AND ORDER ON REMAND"))
        self.assertTrue(_line_is_mspb_title("DECISION GRANTING RELIEF"))
        self.assertFalse(_line_is_mspb_title("BACKGROUND AND PROCEDURAL HISTORY"))


if __name__ == "__main__":
    unittest.main()
