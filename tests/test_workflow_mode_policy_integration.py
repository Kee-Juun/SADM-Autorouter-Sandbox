"""Workflow-level checks that stop before any browser setup."""

import unittest
from unittest.mock import Mock

import pandas as pd

from core.router_modes.orchestration import EMPTY_SCOPE_MESSAGES
from core.smducar_workflow import run_automation_workflow


class WorkflowModePolicyIntegrationTests(unittest.TestCase):
    def test_court_mode_empty_scope_returns_before_browser_setup(self):
        dataframe = pd.DataFrame(
            [
                {
                    "FileName": "LDC_SMD_24-9999.pdf",
                    "CourtCode": "USAP0001",
                    "Status": "",
                }
            ],
            index=[42],
        )
        show_error = Mock()

        counsel_df, main_df = run_automation_workflow(
            latest_excel="not-opened.xlsx",
            df=dataframe,
            itc_mode=True,
            show_error=show_error,
        )

        self.assertTrue(counsel_df.empty)
        self.assertTrue(main_df.empty)
        show_error.assert_called_once_with(EMPTY_SCOPE_MESSAGES["itc"])


if __name__ == "__main__":
    unittest.main()
