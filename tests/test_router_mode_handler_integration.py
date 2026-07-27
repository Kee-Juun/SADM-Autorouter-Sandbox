"""Router-level handler integration tests that do not create a WebDriver."""

import unittest
from unittest.mock import ANY, Mock, call

import pandas as pd

from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


class RouterModeHandlerIntegrationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_fill_irt_form_delegates_to_each_existing_specialized_method(self):
        cases = [
            ("mspb", "fill_mspb_irt_form", True),
            ("itc", "fill_itc_irt_form", False),
            ("irsplr", "fill_irsplr_irt_form", False),
            ("ohtax0", "fill_ohtax0_irt_form", False),
            ("mnsutb", "fill_mnsutb_irt_form", False),
        ]
        row = {"FileName": "document.pdf", "LNI": "LNI-1"}

        for mode_key, method_name, mspb_mode in cases:
            with self.subTest(mode=mode_key):
                router = CaseLawRouter.__new__(CaseLawRouter)
                delegated_method = Mock(return_value=f"{mode_key}-result")
                setattr(router, method_name, delegated_method)
                metadata = object()
                metadata_kwargs = {
                    "mspb_metadata": None,
                    "itc_metadata": None,
                    "irsplr_metadata": None,
                    "ohtax0_metadata": None,
                    "mnsutb_metadata": None,
                }
                metadata_kwargs[f"{mode_key}_metadata"] = metadata

                result = CaseLawRouter.fill_irt_form(
                    router,
                    row,
                    pd.DataFrame(),
                    9,
                    "mapping.xlsx",
                    mspb_mode=mspb_mode,
                    **metadata_kwargs,
                )

                self.assertEqual(f"{mode_key}-result", result)
                delegated_method.assert_called_once_with(row, 9, metadata)

    def test_itc_process_batch_preserves_metadata_call_order_and_form_arguments(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router.safe_alert_accept = Mock()
        router.validate_row = Mock(return_value="LNI-ITC")
        router.search_lni = Mock(return_value=True)
        router.check_result_available = Mock(return_value=True)
        router.record_itc_metadata = Mock()
        extracted = object()
        processed = object()
        router.extract_itc_metadata_from_search_result = Mock(
            return_value=extracted
        )
        router.mark_itc_duplicate_status = Mock(return_value=processed)
        router.click_matching_result = Mock()
        router.open_and_process_form = Mock(return_value="DONE")
        router._should_refresh_retry_form_status = Mock(return_value=False)

        dataframe = pd.DataFrame(
            [
                {
                    "FileName": "itc000_337-1447_20260101.pdf",
                    "CourtCode": "FDITC000",
                    "LNI": "LNI-ITC",
                    "Status": "",
                }
            ],
            index=[4],
        )

        processed_count, _ = CaseLawRouter.process_batch(
            router,
            dataframe,
            dataframe,
            "mapping.xlsx",
            None,
            "itc",
        )

        self.assertEqual(1, processed_count)
        self.assertEqual(
            [
                call(
                    4,
                    ANY,
                    "LNI-ITC",
                    metadata_status="Attempted",
                ),
                call(
                    4,
                    ANY,
                    "LNI-ITC",
                    metadata=processed,
                    metadata_status="Extracted",
                ),
            ],
            router.record_itc_metadata.call_args_list,
        )
        router.extract_itc_metadata_from_search_result.assert_called_once()
        router.mark_itc_duplicate_status.assert_called_once()
        router.click_matching_result.assert_called_once_with()
        router.open_and_process_form.assert_called_once_with(
            ANY,
            dataframe,
            4,
            "mapping.xlsx",
            dar_mode=False,
            wc_mode=False,
            mspb_mode=False,
            mspb_metadata=None,
            itc_metadata=processed,
            irsplr_metadata=None,
            ohtax0_metadata=None,
            mnsutb_metadata=None,
        )


if __name__ == "__main__":
    unittest.main()
