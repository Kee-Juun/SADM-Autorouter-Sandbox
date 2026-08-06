"""Offline contracts for Chrome/ChromeDriver version resolution."""

import unittest
from unittest.mock import Mock, call, patch

from core import chromedriver_resolver


class ChromeDriverResolverTests(unittest.TestCase):
    def setUp(self):
        self.bundled_candidates = patch.object(
            chromedriver_resolver,
            "_candidate_bundled_chromedriver_paths",
            return_value=[],
        )
        self.cached_candidates = patch.object(
            chromedriver_resolver,
            "_candidate_cached_chromedriver_paths",
            return_value=[],
        )
        self.bundled_candidates.start()
        self.cached_candidates.start()
        self.addCleanup(self.bundled_candidates.stop)
        self.addCleanup(self.cached_candidates.stop)

    def test_version_parsing_and_major_extraction(self):
        self.assertEqual(
            "126.0.6478.127",
            chromedriver_resolver._parse_version(
                "Google Chrome 126.0.6478.127"
            ),
        )
        self.assertEqual(
            "126",
            chromedriver_resolver._major(
                "ChromeDriver 126.0.6478.126"
            ),
        )
        self.assertIsNone(chromedriver_resolver._parse_version("unknown"))

    def test_matching_detected_and_driver_versions_return_path(self):
        with (
            patch.object(
                chromedriver_resolver,
                "detect_chrome_version",
                return_value="126.0.6478.127",
            ),
            patch.object(
                chromedriver_resolver,
                "_install_driver",
                return_value=r"C:\driver\chromedriver.exe",
            ) as install,
            patch.object(
                chromedriver_resolver,
                "_get_chromedriver_version",
                return_value="126.0.6478.126",
            ),
        ):
            result = chromedriver_resolver.resolve_chromedriver_path()

        self.assertEqual(r"C:\driver\chromedriver.exe", result)
        install.assert_called_once_with("126.0.6478.127")

    def test_matching_existing_driver_is_used_before_download(self):
        bundled = r"C:\app\drivers\chromedriver.exe"
        with (
            patch.object(
                chromedriver_resolver,
                "detect_chrome_version",
                return_value="126.0.6478.127",
            ),
            patch.object(
                chromedriver_resolver,
                "_candidate_bundled_chromedriver_paths",
                return_value=[bundled],
            ),
            patch.object(
                chromedriver_resolver,
                "_get_chromedriver_version",
                return_value="126.0.6478.126",
            ),
            patch.object(chromedriver_resolver, "_install_driver") as install,
        ):
            result = chromedriver_resolver.resolve_chromedriver_path()

        self.assertEqual(bundled, result)
        install.assert_not_called()

    def test_incompatible_existing_driver_falls_back_to_download(self):
        bundled = r"C:\app\drivers\chromedriver.exe"
        downloaded = r"C:\download\chromedriver.exe"
        with (
            patch.object(
                chromedriver_resolver,
                "detect_chrome_version",
                return_value="126.0.6478.127",
            ),
            patch.object(
                chromedriver_resolver,
                "_candidate_bundled_chromedriver_paths",
                return_value=[bundled],
            ),
            patch.object(
                chromedriver_resolver,
                "_install_driver",
                return_value=downloaded,
            ) as install,
            patch.object(
                chromedriver_resolver,
                "_get_chromedriver_version",
                side_effect=["125.0.0.0", "126.0.6478.126"],
            ),
        ):
            result = chromedriver_resolver.resolve_chromedriver_path()

        self.assertEqual(downloaded, result)
        install.assert_called_once_with("126.0.6478.127")

    def test_major_mismatch_clears_cache_and_retries_default_detection(self):
        with (
            patch.object(
                chromedriver_resolver,
                "detect_chrome_version",
                return_value="126.0.6478.127",
            ),
            patch.object(
                chromedriver_resolver,
                "_install_driver",
                side_effect=[
                    r"C:\driver\wrong\chromedriver.exe",
                    r"C:\driver\right\chromedriver.exe",
                ],
            ) as install,
            patch.object(
                chromedriver_resolver,
                "_get_chromedriver_version",
                side_effect=[
                    "114.0.5735.90",
                    "126.0.6478.126",
                ],
            ),
            patch.object(
                chromedriver_resolver,
                "_clear_chromedriver_cache",
            ) as clear_cache,
        ):
            result = chromedriver_resolver.resolve_chromedriver_path()

        self.assertEqual(r"C:\driver\right\chromedriver.exe", result)
        self.assertEqual(
            [call("126.0.6478.127"), call(None)],
            install.call_args_list,
        )
        clear_cache.assert_called_once_with()

    def test_unknown_chrome_version_uses_default_manager_attempt(self):
        with (
            patch.object(
                chromedriver_resolver,
                "detect_chrome_version",
                return_value=None,
            ),
            patch.object(
                chromedriver_resolver,
                "_install_driver",
                return_value=r"C:\driver\chromedriver.exe",
            ) as install,
            patch.object(
                chromedriver_resolver,
                "_get_chromedriver_version",
                return_value="126.0.6478.126",
            ),
        ):
            result = chromedriver_resolver.resolve_chromedriver_path()

        self.assertEqual(r"C:\driver\chromedriver.exe", result)
        install.assert_called_once_with(None)

    def test_resolution_failure_raises_actionable_message(self):
        with (
            patch.object(
                chromedriver_resolver,
                "detect_chrome_version",
                return_value=None,
            ),
            patch.object(
                chromedriver_resolver,
                "_install_driver",
                side_effect=RuntimeError("download failed"),
            ),
            self.assertRaisesRegex(
                Exception,
                "no compatible cached/bundled driver was found",
            ),
        ):
            chromedriver_resolver.resolve_chromedriver_path()

    def test_workflow_resolver_delegates_to_shared_resolver(self):
        from core import smducar_workflow

        with patch.object(
            smducar_workflow,
            "resolve_compatible_chromedriver_path",
            return_value=r"C:\driver\chromedriver.exe",
        ) as shared_resolver:
            result = smducar_workflow._resolve_chromedriver_path()

        self.assertEqual(r"C:\driver\chromedriver.exe", result)
        shared_resolver.assert_called_once_with()

    def test_direct_selenium_launcher_uses_shared_resolver(self):
        from core import smducar_selenium

        driver = Mock()
        with (
            patch.object(
                smducar_selenium,
                "load_config",
                return_value={"headless": True},
            ),
            patch.object(
                smducar_selenium,
                "resolve_chromedriver_path",
                return_value=r"C:\driver\chromedriver.exe",
            ) as shared_resolver,
            patch.object(smducar_selenium, "ChromeService") as service_class,
            patch.object(
                smducar_selenium,
                "ChromeWebDriver",
                return_value=driver,
            ),
        ):
            result = smducar_selenium.launch_chrome_driver()

        self.assertIs(driver, result)
        shared_resolver.assert_called_once_with()
        service_class.assert_called_once_with(
            r"C:\driver\chromedriver.exe"
        )


if __name__ == "__main__":
    unittest.main()
