import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import path_safety


def load_script(name: str):
    script = SCRIPTS / name
    spec = importlib.util.spec_from_file_location(script.stem, script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


CONVERT = load_script("convert_full_note_embeds_to_links.py")


class PathSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base = Path(self.temp_dir.name)
        self.workspace = self.base / "workspace"
        self.assets = self.workspace / "data" / "assets"
        self.assets.mkdir(parents=True)
        self.vault = self.base / "vault"
        self.vault.mkdir()
        (self.vault / "attachments").mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_asset_percent_encoded_slash_uses_safe_basename(self):
        (self.assets / "image.png").write_bytes(b"image")
        source, destination, filename = path_safety.resolve_asset_paths(
            self.workspace, self.vault, "assets/folder%2Fimage.png", "attachments"
        )
        self.assertEqual(filename, "image.png")
        self.assertEqual(source, (self.assets / "image.png").resolve())
        self.assertEqual(destination, (self.vault / "attachments" / "image.png").resolve())

    def test_asset_encoded_backslash_uses_safe_basename(self):
        (self.assets / "image.png").write_bytes(b"image")
        _, _, filename = path_safety.resolve_asset_paths(
            self.workspace, self.vault, r"assets%5Cfolder%5Cimage.png", "attachments"
        )
        self.assertEqual(filename, "image.png")

    def test_asset_empty_filename_is_rejected(self):
        with self.assertRaises(ValueError):
            path_safety.resolve_asset_paths(
                self.workspace, self.vault, "", "attachments"
            )

    def test_asset_dot_filename_is_rejected(self):
        with self.assertRaises(ValueError):
            path_safety.resolve_asset_paths(
                self.workspace, self.vault, ".", "attachments"
            )

    def test_asset_dotdot_filename_is_rejected(self):
        with self.assertRaises(ValueError):
            path_safety.resolve_asset_paths(
                self.workspace, self.vault, "%2E%2E", "attachments"
            )

    def test_asset_source_and_destination_are_contained(self):
        (self.assets / "safe.png").write_bytes(b"image")
        source, destination, _ = path_safety.resolve_asset_paths(
            self.workspace, self.vault, "assets/safe.png", "attachments"
        )
        self.assertIn(self.assets.resolve(), source.parents)
        self.assertIn((self.vault / "attachments").resolve(), destination.parents)

    def test_asset_source_symlink_escape_is_rejected(self):
        outside = self.base / "outside.png"
        outside.write_bytes(b"secret")
        (self.assets / "escape.png").symlink_to(outside)
        with self.assertRaises(ValueError):
            path_safety.resolve_asset_paths(
                self.workspace, self.vault, "assets/escape.png", "attachments"
            )

    def test_asset_destination_symlink_escape_is_rejected(self):
        (self.assets / "safe.png").write_bytes(b"image")
        outside = self.base / "outside"
        outside.mkdir()
        (self.vault / "linked-attachments").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            path_safety.resolve_asset_paths(
                self.workspace, self.vault, "assets/safe.png", "linked-attachments"
            )

    def test_notebook_absolute_path_is_rejected(self):
        with self.assertRaises(ValueError):
            CONVERT.resolve_notebook_dirs(self.vault, ["/tmp/outside"])

    def test_notebook_parent_traversal_is_rejected(self):
        with self.assertRaises(ValueError):
            CONVERT.resolve_notebook_dirs(self.vault, ["../outside"])

    def test_notebook_vault_root_is_rejected(self):
        with self.assertRaises(ValueError):
            CONVERT.resolve_notebook_dirs(self.vault, ["folder/.."])

    def test_notebook_symlink_escape_is_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        (self.vault / "linked").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            CONVERT.resolve_notebook_dirs(self.vault, ["linked"])

    def test_notebook_legal_subdirectory_is_allowed(self):
        expected = self.vault / "source-notebook" / "target-folder"
        expected.mkdir(parents=True)
        self.assertEqual(
            CONVERT.resolve_notebook_dirs(self.vault, ["source-notebook/target-folder"]),
            [expected.resolve()],
        )


if __name__ == "__main__":
    unittest.main()
