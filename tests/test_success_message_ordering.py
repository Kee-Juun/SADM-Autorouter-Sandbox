"""Offline GUI-summary contracts for the August 16 parent sync."""

import unittest
from types import SimpleNamespace

from frontend.smducar_pyqt import SMDUSAPGui


class SuccessMessageOrderingTests(unittest.TestCase):
    def _message(self, mode, **overrides):
        counts = {
            "counsel_success": 2,
            "main_success": 3,
            "counsel_already": 4,
            "main_already": 5,
            "counsel_timeout": 0,
            "main_timeout": 0,
        }
        counts.update(overrides)
        gui = SimpleNamespace(config={"mode": mode})
        return SMDUSAPGui.get_success_message(
            gui,
            "Kevin",
            counts["counsel_success"],
            counts["main_success"],
            counts["counsel_already"],
            counts["main_already"],
            counsel_timeout=counts["counsel_timeout"],
            main_timeout=counts["main_timeout"],
        )

    def test_success_section_precedes_already_processed_for_every_mode(self):
        for mode in ("mspb", "itc", "irsplr", "ohtax0", "mnsutb", "dar", "smd"):
            with self.subTest(mode=mode):
                message = self._message(mode)
                self.assertLess(
                    message.index("Successfully auto-routed:"),
                    message.index("Already processed:"),
                )

    def test_already_processed_precedes_timeout_section(self):
        for mode in ("itc", "irsplr", "ohtax0", "mnsutb", "dar", "smd"):
            with self.subTest(mode=mode):
                message = self._message(
                    mode,
                    counsel_timeout=1,
                    main_timeout=2,
                )
                self.assertLess(
                    message.index("Already processed:"),
                    message.index("Timeout issues:"),
                )

    def test_zero_new_routes_omits_success_section(self):
        message = self._message(
            "mspb",
            counsel_success=0,
            main_success=0,
        )

        self.assertNotIn("Successfully auto-routed:", message)
        self.assertIn("Already processed:\nMSPB: 5", message)


if __name__ == "__main__":
    unittest.main()
