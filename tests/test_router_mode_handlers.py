"""Call-trace contracts for delegating document-mode handlers."""

import ast
import unittest
from pathlib import Path
from unittest.mock import Mock

from core.router_modes.handlers import (
    DOCUMENT_MODE_HANDLERS,
    get_document_mode_handler,
    select_form_mode_handler,
    select_row_mode_handler,
)


class RouterModeHandlerTests(unittest.TestCase):
    def test_registry_contains_only_existing_specialized_document_modes(self):
        self.assertEqual(
            ["mspb", "itc", "irsplr", "ohtax0", "mnsutb", "mework", "mosu00"],
            list(DOCUMENT_MODE_HANDLERS),
        )

    def test_each_handler_delegates_record_extract_and_fill_exactly(self):
        for mode_key, handler in DOCUMENT_MODE_HANDLERS.items():
            with self.subTest(mode=mode_key):
                router = Mock()
                recorded = object()
                extracted = object()
                filled = object()
                getattr(router, handler.record_method_name).return_value = recorded
                getattr(router, handler.extract_method_name).return_value = extracted
                getattr(router, handler.fill_method_name).return_value = filled
                row = object()
                metadata = object()

                self.assertIs(
                    recorded,
                    handler.record_metadata(
                        router,
                        7,
                        row,
                        "LNI-1",
                        metadata=metadata,
                        metadata_status="Extracted",
                    ),
                )
                getattr(router, handler.record_method_name).assert_called_once_with(
                    7,
                    row,
                    "LNI-1",
                    metadata=metadata,
                    metadata_status="Extracted",
                )

                self.assertIs(extracted, handler.extract_metadata(router, row, 7))
                getattr(router, handler.extract_method_name).assert_called_once_with(
                    row,
                    7,
                )

                self.assertIs(filled, handler.fill_form(router, row, 7, metadata))
                getattr(router, handler.fill_method_name).assert_called_once_with(
                    row,
                    7,
                    metadata,
                )

    def test_only_itc_delegates_metadata_postprocessing(self):
        metadata = object()
        row = object()

        for mode_key, handler in DOCUMENT_MODE_HANDLERS.items():
            with self.subTest(mode=mode_key):
                router = Mock()
                if mode_key in {"itc", "mework"}:
                    processed = object()
                    postprocess_method = getattr(router, handler.postprocess_method_name)
                    postprocess_method.return_value = processed
                    self.assertIs(
                        processed,
                        handler.postprocess_metadata(
                            router,
                            3,
                            row,
                            "LNI-2",
                            metadata,
                        ),
                    )
                    postprocess_method.assert_called_once_with(
                        3,
                        row,
                        "LNI-2",
                        metadata,
                    )
                else:
                    self.assertIs(
                        metadata,
                        handler.postprocess_metadata(
                            router,
                            3,
                            row,
                            "LNI-2",
                            metadata,
                        ),
                    )

    def test_recording_without_metadata_preserves_legacy_call_shape(self):
        handler = get_document_mode_handler("mspb")
        router = Mock()
        row = object()

        handler.record_metadata(
            router,
            5,
            row,
            "LNI-3",
            metadata_status="Attempted",
        )

        router.record_mspb_metadata.assert_called_once_with(
            5,
            row,
            "LNI-3",
            metadata_status="Attempted",
        )

    def test_row_handler_selection_preserves_existing_precedence(self):
        all_true = select_row_mode_handler(
            mspb_mode=True,
            row_is_itc=True,
            irsplr_mode=True,
            row_is_irsplr=True,
            ohtax0_mode=True,
            row_is_ohtax0=True,
            mnsutb_mode=True,
            row_is_mnsutb=True,
        )
        self.assertEqual("mspb", all_true.key)

        cases = [
            ({"row_is_itc": True, "irsplr_mode": True}, "itc"),
            ({"irsplr_mode": True, "row_is_ohtax0": True}, "irsplr"),
            ({"row_is_irsplr": True, "ohtax0_mode": True}, "irsplr"),
            ({"ohtax0_mode": True, "row_is_mnsutb": True}, "ohtax0"),
            ({"row_is_ohtax0": True, "mnsutb_mode": True}, "ohtax0"),
            ({"mnsutb_mode": True}, "mnsutb"),
            ({"row_is_mnsutb": True}, "mnsutb"),
        ]
        for kwargs, expected in cases:
            with self.subTest(kwargs=kwargs):
                self.assertEqual(
                    expected,
                    select_row_mode_handler(**kwargs).key,
                )

        self.assertIsNone(select_row_mode_handler())

    def test_form_handler_selection_preserves_metadata_precedence(self):
        metadata = {
            "mspb": object(),
            "itc": object(),
            "irsplr": object(),
            "ohtax0": object(),
            "mnsutb": object(),
        }
        self.assertEqual(
            "mspb",
            select_form_mode_handler(
                mspb_mode=True,
                metadata_by_mode=metadata,
            ).key,
        )
        self.assertEqual(
            "itc",
            select_form_mode_handler(metadata_by_mode=metadata).key,
        )

        metadata["itc"] = None
        self.assertEqual(
            "irsplr",
            select_form_mode_handler(metadata_by_mode=metadata).key,
        )
        metadata["irsplr"] = None
        self.assertEqual(
            "ohtax0",
            select_form_mode_handler(metadata_by_mode=metadata).key,
        )
        metadata["ohtax0"] = None
        self.assertEqual(
            "mnsutb",
            select_form_mode_handler(metadata_by_mode=metadata).key,
        )
        metadata["mnsutb"] = None
        self.assertIsNone(select_form_mode_handler(metadata_by_mode=metadata))

    def test_unknown_specialized_handler_raises(self):
        with self.assertRaises(KeyError):
            get_document_mode_handler("smd")

    def test_handler_module_has_no_router_or_selenium_imports(self):
        handler_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "handlers.py"
        )
        tree = ast.parse(handler_path.read_text(encoding="utf-8"))
        imported_roots = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_roots.update(
                    alias.name.split(".", 1)[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_roots.add(node.module.split(".", 1)[0])

        self.assertTrue(
            imported_roots.isdisjoint(
                {"selenium", "smducar_router", "smducar_workflow"}
            ),
            imported_roots,
        )
        source = handler_path.read_text(encoding="utf-8")
        for selenium_detail in (
            "By.XPATH",
            "WebDriverWait",
            "expected_conditions",
            "//*[@id=",
            "Outside Conversion",
            'select_by_visible_text("Archive")',
        ):
            with self.subTest(selenium_detail=selenium_detail):
                self.assertNotIn(selenium_detail, source)


if __name__ == "__main__":
    unittest.main()
