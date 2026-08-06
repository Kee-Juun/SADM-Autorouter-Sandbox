"""Offline contracts for the current notification formatting and playbooks."""

import datetime
import tempfile
import unittest
from pathlib import Path

from core import critical_error_notifier as notifier


class CriticalErrorNotifierCurrentSyncTests(unittest.TestCase):
    def test_subject_uses_application_mode_and_readable_timestamp(self):
        theme = {"subject": "Run needs a quick review"}

        subject = notifier._critical_subject(
            "mspb",
            datetime.datetime(2026, 8, 7, 15, 4, 5),
            theme=theme,
        )

        self.assertEqual(
            "SADM Autorouter: MSPB - Run needs a quick review - "
            "08/07/2026 03:04:05 PM",
            subject,
        )

    def test_rerun_preview_accepts_row_alias(self):
        summary = {
            "rerun_rows": [
                {"Row": 14, "LNI": "1234567890", "Status": "NEEDS RERUN"}
            ]
        }

        lines = notifier._format_run_status_examples(summary)

        self.assertIn("- Row 14: 1234567890 (NEEDS RERUN)", lines)

    def test_session_loss_body_contains_targeted_playbook(self):
        payload = {
            "title": "Router session lost",
            "error": "invalid session id",
            "mode": "mspb",
            "run_status_summary": {
                "done_count": 1,
                "already_processed_count": 0,
                "needs_rerun_count": 1,
                "counts": {"NEEDS RERUN": 1},
                "rerun_rows": [
                    {"Excel Row": 3, "LNI": "9876543210", "Status": "NEEDS RERUN"}
                ],
            },
        }
        theme = {
            "hello": "Heads up,",
            "opener": "{app_name} paused.",
            "snapshot": "What happened:",
            "attachments": "Files attached.",
            "closer": "Review ready.",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            body = notifier._build_critical_email_body(
                payload,
                Path(temp_dir),
                theme=theme,
            )

        self.assertIn("Rows to rerun preview:", body)
        self.assertIn("- Row 3: 9876543210 (NEEDS RERUN)", body)
        self.assertIn("Close any leftover Chrome windows", body)
        self.assertIn("Suggested next steps:", body)


if __name__ == "__main__":
    unittest.main()
