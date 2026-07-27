"""Business-compliance contract for the MNSUTB IRT Source Detail."""

import unittest
from unittest.mock import Mock

from core.mnsutb_extractor import (
    MNSUTBMetadata,
    MNSUTB_SOURCE_DETAIL,
    classify_mnsutb_source_detail,
    parse_mnsutb_document_text,
)
from core.smducar_excel import get_source_detail_mapping
from core.smducar_router import CaseLawRouter
from frontend.pyqt_utils import extract_source_detail_from_filename


class MnsutbSourceDetailComplianceTests(unittest.TestCase):
    def test_order_title_maps_to_required_source_detail(self):
        self.assertEqual(
            "Table-(5-day spec source)",
            MNSUTB_SOURCE_DETAIL,
        )
        self.assertEqual(
            MNSUTB_SOURCE_DETAIL,
            classify_mnsutb_source_detail("Order"),
        )
        self.assertNotEqual(
            "Order",
            classify_mnsutb_source_detail("Order"),
        )

    def test_parsed_metadata_carries_required_source_detail(self):
        metadata = parse_mnsutb_document_text(
            "\n".join(
                (
                    "STATE OF MINNESOTA",
                    "IN SUPREME COURT",
                    "A24-12345",
                    "ORDER",
                    "Dated: January 2, 2026",
                    "BY THE COURT:",
                )
            ),
            filename_hint="LDC_SMD_A24-12345.pdf",
        )

        self.assertIsNotNone(metadata)
        self.assertEqual(MNSUTB_SOURCE_DETAIL, metadata.source_detail)

    def test_form_field_helper_selects_compliant_metadata_value(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        case_name_field = Mock()
        router.wait = Mock()
        router.wait.until.return_value = case_name_field
        router.wait_for_existing_field_text = Mock(return_value="Existing")
        router.select_source_detail = Mock(return_value=True)
        router.append_comments = Mock(return_value=True)
        metadata = MNSUTBMetadata(
            court="STMNSUTB",
            docket_number="A24-12345",
            decision_date="01-02-2026",
            source_detail=MNSUTB_SOURCE_DETAIL,
        )

        result = CaseLawRouter.handle_mnsutb_fields(
            router,
            {"Comments": ""},
            metadata,
        )

        self.assertTrue(result)
        router.select_source_detail.assert_called_once_with(
            "Table-(5-day spec source)"
        )

    def test_excel_and_filename_mappings_use_compliant_value(self):
        self.assertEqual(
            MNSUTB_SOURCE_DETAIL,
            get_source_detail_mapping()["t"],
        )
        self.assertEqual(
            MNSUTB_SOURCE_DETAIL,
            extract_source_detail_from_filename(
                "LDC_SMD_24-7640_t.pdf"
            ),
        )


if __name__ == "__main__":
    unittest.main()
