"""Regression coverage for strict readable-text ITC docket fallback."""

import unittest

from core.itc_extractor import resolve_itc_docket_number


class ItcFilenameFallbackCurrentSyncTests(unittest.TestCase):
    def test_itc_like_text_without_primary_docket_uses_filename(self):
        docket, used_fallback = resolve_itc_docket_number(
            "UNITED STATES INTERNATIONAL TRADE COMMISSION\nCommission Notice",
            "ITC000_337-1447_20260903.pdf",
            True,
            None,
            "FDITC000",
        )
        self.assertEqual("337-TA-1447", docket)
        self.assertTrue(used_fallback)

    def test_conflicting_loose_docket_blocks_filename_fallback(self):
        docket, used_fallback = resolve_itc_docket_number(
            "UNITED STATES INTERNATIONAL TRADE COMMISSION\nInvestigation No. 337-9999",
            "ITC000_337-1447_20260903.pdf",
            True,
            None,
            "FDITC000",
        )
        self.assertIsNone(docket)
        self.assertFalse(used_fallback)

    def test_non_itc_readable_text_blocks_filename_fallback(self):
        docket, used_fallback = resolve_itc_docket_number(
            "An unrelated readable court document",
            "ITC000_337-1447_20260903.pdf",
            True,
            None,
            "FDITC000",
        )
        self.assertIsNone(docket)
        self.assertFalse(used_fallback)


if __name__ == "__main__":
    unittest.main()
