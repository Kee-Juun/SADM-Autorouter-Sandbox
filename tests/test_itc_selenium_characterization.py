"""No-driver characterization tests for the current ITC form flow."""

import ast
import importlib.util
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, call, patch

from core.itc_extractor import ITCMetadata
from core.smducar_config import status_updates_buffer
from core.smducar_router import CaseLawRouter


def _selenium_symbol(name):
    if importlib.util.find_spec("core.router_modes.itc_selenium"):
        return f"core.router_modes.itc_selenium.{name}"
    return f"core.smducar_router.{name}"


def _metadata(*, duplicate=False, excluded=False):
    return ITCMetadata(
        court="FDITC000",
        docket_number="337-TA-1447",
        decision_date="01-02-2026",
        source_detail="Excluded" if excluded else "Opinion",
        is_true_duplicate=duplicate,
        duplicate_of="fingerprint" if duplicate else "",
        duplicate_of_lni="LNI-OLD" if duplicate else "",
        is_excluded=excluded,
        exclusion_reason="Excluded document" if excluded else "",
    )


class ITCSeleniumCharacterizationTests(unittest.TestCase):
    def tearDown(self):
        status_updates_buffer.clear()

    def test_missing_metadata_preserves_skip_and_restores_duplicate_policy(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router._archive_duplicate_mode = True

        result = CaseLawRouter.fill_itc_irt_form(
            router,
            {"FileName": "itc000_337-1447_20260102.pdf"},
            48,
            None,
        )

        self.assertEqual("SKIPPED: ITC PDF DATA NOT FOUND", result)
        self.assertEqual("SKIPPED: ITC PDF DATA NOT FOUND", status_updates_buffer[48])
        self.assertTrue(router._archive_duplicate_mode)

    def test_locked_excluded_form_remains_already_processed(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router._archive_duplicate_mode = False
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.is_locked_archive_excluded_form = Mock(return_value=True)
        router.driver = Mock()
        router.driver.window_handles = ["main"]
        metadata = _metadata(excluded=True)

        result = CaseLawRouter.fill_itc_irt_form(
            router,
            {"FileName": "itc000_337-1447_20260102.pdf"},
            49,
            metadata,
        )

        self.assertEqual("ALREADY PROCESSED", result)
        self.assertEqual("ALREADY PROCESSED", status_updates_buffer[49])
        router.is_locked_archive_excluded_form.assert_called_once_with("ITC")
        self.assertFalse(router._archive_duplicate_mode)

    def test_enabled_route_preserves_normal_duplicate_and_excluded_policies(self):
        cases = [
            (False, False, "Outside Conversion"),
            (True, False, "Archive"),
            (False, True, "Archive"),
        ]
        for duplicate, excluded, expected_route in cases:
            with self.subTest(
                duplicate=duplicate,
                excluded=excluded,
                expected_route=expected_route,
            ):
                router = CaseLawRouter.__new__(CaseLawRouter)
                router._archive_duplicate_mode = False
                observed_duplicate_policy = []
                router.prepare_common_fields = Mock()
                router.handle_any_alert = Mock()
                router.is_locked_archive_excluded_form = Mock(return_value=False)
                router.handle_itc_fields = Mock(
                    side_effect=lambda *_: (
                        observed_duplicate_policy.append(
                            router._archive_duplicate_mode
                        )
                        or True
                    )
                )
                router.click_ready_checkbox_and_check_overlay = Mock(
                    return_value=False
                )
                router.handle_routing_and_save = Mock(
                    side_effect=lambda *_args, **_kwargs: (
                        observed_duplicate_policy.append(
                            router._archive_duplicate_mode
                        )
                        or "DONE"
                    )
                )
                comments = Mock()
                comments.is_enabled.return_value = True
                route = Mock()
                route.is_enabled.return_value = True
                router.wait = Mock()
                router.wait.until.side_effect = [comments, route, route]
                router.driver = Mock()
                clickable_wait = Mock()
                clickable_wait.until.return_value = route
                dropdown = Mock()
                metadata = _metadata(duplicate=duplicate, excluded=excluded)
                row = {"FileName": "itc000_337-1447_20260102.pdf"}

                with ExitStack() as stack:
                    webdriver_wait = stack.enter_context(
                        patch(_selenium_symbol("WebDriverWait"))
                    )
                    select = stack.enter_context(
                        patch(_selenium_symbol("Select"))
                    )
                    webdriver_wait.return_value = clickable_wait
                    select.return_value = dropdown
                    result = CaseLawRouter.fill_itc_irt_form(
                        router,
                        row,
                        50,
                        metadata,
                    )

                self.assertEqual("DONE", result)
                dropdown.select_by_visible_text.assert_called_once_with(
                    expected_route
                )
                self.assertEqual(
                    [duplicate, duplicate],
                    observed_duplicate_policy,
                )
                self.assertFalse(router._archive_duplicate_mode)
                router.prepare_common_fields.assert_called_once_with(
                    "itc000_337-1447_20260102.pdf",
                    decision_date="01-02-2026",
                    dar_mode=False,
                    wc_mode=False,
                    docket_override="337-TA-1447",
                    court="FDITC000",
                )
                router.click_ready_checkbox_and_check_overlay.assert_called_once_with(
                    False
                )
                router.handle_routing_and_save.assert_called_once_with(
                    False,
                    50,
                    skip_route_and_ready=True,
                )
                self.assertEqual(
                    [call(), call(), call(), call(), call()],
                    router.handle_any_alert.call_args_list,
                )

    def test_disabled_excluded_route_preserves_confirmed_archive_path(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router._archive_duplicate_mode = False
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.is_locked_archive_excluded_form = Mock(return_value=False)
        router.handle_itc_fields = Mock(return_value=True)
        router.get_selected_dropdown_text = Mock(return_value="Archive")
        router.dropdown_text_matches = Mock(return_value=True)
        router.set_dropdown_by_visible_text = Mock()
        router.click_ready_checkbox_and_check_overlay = Mock(return_value=False)
        router.handle_routing_and_save = Mock(return_value="DONE")
        comments = Mock()
        comments.is_enabled.return_value = True
        route = Mock()
        route.is_enabled.return_value = False
        router.wait = Mock()
        router.wait.until.side_effect = [comments, route, route]
        router.driver = Mock()

        result = CaseLawRouter.fill_itc_irt_form(
            router,
            {"FileName": "itc000_337-1447_20260102.pdf"},
            51,
            _metadata(excluded=True),
        )

        self.assertEqual("DONE", result)
        self.assertEqual(2, router.get_selected_dropdown_text.call_count)
        router.dropdown_text_matches.assert_called_once_with("Archive", "Archive")
        router.set_dropdown_by_visible_text.assert_not_called()
        self.assertFalse(router._archive_duplicate_mode)

    def test_nonexcluded_disabled_route_remains_already_processed(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router._archive_duplicate_mode = False
        router.prepare_common_fields = Mock()
        router.handle_any_alert = Mock()
        router.handle_itc_fields = Mock(return_value=True)
        comments = Mock()
        comments.is_enabled.return_value = True
        route = Mock()
        route.is_enabled.return_value = False
        router.wait = Mock()
        router.wait.until.side_effect = [comments, route]
        router.driver = Mock()
        router.driver.window_handles = ["main"]

        result = CaseLawRouter.fill_itc_irt_form(
            router,
            {"FileName": "itc000_337-1447_20260102.pdf"},
            52,
            _metadata(duplicate=True),
        )

        self.assertEqual("ALREADY PROCESSED", result)
        self.assertEqual("ALREADY PROCESSED", status_updates_buffer[52])
        self.assertFalse(router._archive_duplicate_mode)

    def test_unexpected_error_restores_duplicate_policy(self):
        router = CaseLawRouter.__new__(CaseLawRouter)
        router._archive_duplicate_mode = False
        router.prepare_common_fields = Mock(side_effect=RuntimeError("boom"))

        result = CaseLawRouter.fill_itc_irt_form(
            router,
            {"FileName": "itc000_337-1447_20260102.pdf"},
            53,
            _metadata(duplicate=True),
        )

        self.assertEqual("ERROR", result)
        self.assertEqual("ERROR", status_updates_buffer[53])
        self.assertFalse(router._archive_duplicate_mode)

    def test_case_law_router_keeps_only_the_compatibility_entry_point(self):
        router_path = (
            Path(__file__).resolve().parents[1] / "core" / "smducar_router.py"
        )
        tree = ast.parse(router_path.read_text(encoding="utf-8"))
        method = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name == "fill_itc_irt_form"
        )
        executable_body = [
            statement
            for statement in method.body
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ]

        self.assertEqual(1, len(executable_body))
        self.assertIsInstance(executable_body[0], ast.Return)

    def test_extracted_module_contains_only_itc_mode_flow(self):
        module_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "itc_selenium.py"
        )
        source = module_path.read_text(encoding="utf-8")

        self.assertIn("Outside Conversion", source)
        self.assertIn("Archive", source)
        self.assertIn("_archive_duplicate_mode", source)
        for other_mode in ("MSPB", "IRSPLR", "OHTAX0", "MNSUTB"):
            with self.subTest(other_mode=other_mode):
                self.assertNotIn(other_mode, source)


if __name__ == "__main__":
    unittest.main()
