"""Contract tests for the data-only router-mode registry."""

import ast
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

from core.router_modes import (
    MODE_REGISTRY,
    MODE_SPECS,
    get_mode_spec,
    iter_mode_specs,
)


EXPECTED_OPTIONS = [
    ("smd", "SMD Autorouter"),
    ("dar", "DAR Autoruter"),
    ("mspb", "MSPB Autorouter"),
    ("itc", "ITC Autorouter"),
    ("irsplr", "IRSPLR Autorouter"),
    ("ohtax0", "OHTAX0 Autorouter"),
    ("mnsutb", "MNSUTB Autorouter"),
]


class RouterModeRegistryTests(unittest.TestCase):
    def test_selectable_mode_order_and_labels_match_existing_gui_contract(self):
        actual = [(mode.key, mode.display_name) for mode in iter_mode_specs()]

        self.assertEqual(EXPECTED_OPTIONS, actual)

    def test_mode_keys_are_unique_and_registry_matches_ordered_specs(self):
        keys = [mode.key for mode in MODE_SPECS]

        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(keys, list(MODE_REGISTRY))
        self.assertEqual(set(keys), set(MODE_REGISTRY))

    def test_document_only_classification_matches_current_batch_shape(self):
        document_only = {
            mode.key for mode in MODE_SPECS if mode.document_only
        }

        self.assertEqual(
            {"mspb", "itc", "irsplr", "ohtax0", "mnsutb"},
            document_only,
        )

    def test_lookup_returns_registered_spec_and_unknown_key_raises(self):
        self.assertIs(get_mode_spec("itc"), MODE_REGISTRY["itc"])

        with self.assertRaises(KeyError):
            get_mode_spec("unknown")

    def test_specs_and_registry_are_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            MODE_SPECS[0].display_name = "Changed"

        with self.assertRaises(TypeError):
            MODE_REGISTRY["new"] = MODE_SPECS[0]

    def test_registry_has_no_gui_workflow_parser_or_selenium_imports(self):
        registry_path = (
            Path(__file__).resolve().parents[1]
            / "core"
            / "router_modes"
            / "registry.py"
        )
        tree = ast.parse(registry_path.read_text(encoding="utf-8"))
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
                {
                    "PyQt5",
                    "pandas",
                    "selenium",
                    "frontend",
                    "smducar_workflow",
                    "smducar_router",
                }
            ),
            imported_roots,
        )


if __name__ == "__main__":
    unittest.main()
