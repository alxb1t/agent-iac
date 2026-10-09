"""The vendored git-hook plugin is byte for byte its pinned commit. Pin: 0003-the-knowledge-base design D8."""

import hashlib

from conftest import ROOT

PLUGIN = ROOT / "blueprints" / "base" / "plugins" / "git-hook"

# SHA-256 of each file at commit a7303c8 of https://github.com/aean0x/hermes-git-hook.
PINNED = {
    "LICENSE": "465dbda8220e2c8252b6b5fdfe323cb17bcfa30f42f65299c35d2dcff2f7a65b",
    "README.md": "1bf76997338d2997f32a32c0be94ecaa4699e8058a6185a4e11542662d6ce263",
    "__init__.py": "e1b5a9caadb79156f6870ea1e25b19757148c44789659ffcfc66af0068df1b3b",
    "plugin.yaml": "b7f59782888b9cbbf049a0313639adbbe3897752caf17943ec252110c67728e5",
    "sync.py": "591f6a7343d70a63e5c0ef79e58f4ff0bae9bb5799ccbfd7143f637d850554e5",
}


def drift(directory):
    """Return each file not matching its pin, extra or missing, e.g. an edited sync.py → ["sync.py"]."""
    found = {str(p.relative_to(directory)): p for p in directory.rglob("*") if p.is_file()}
    changed = [n for n, p in found.items() if hashlib.sha256(p.read_bytes()).hexdigest() != PINNED.get(n)]
    return sorted(changed + [n for n in PINNED if n not in found])


def test_vendored_plugin_matches_its_pin():
    assert drift(PLUGIN) == []


def test_drift_catches_an_edit_an_extra_file_and_a_missing_one(tmp_path):
    for name in PINNED:
        (tmp_path / name).write_bytes((PLUGIN / name).read_bytes())
    (tmp_path / "sync.py").write_text("edited")
    (tmp_path / "extra.py").write_text("")
    (tmp_path / "LICENSE").unlink()
    assert drift(tmp_path) == ["LICENSE", "extra.py", "sync.py"]
