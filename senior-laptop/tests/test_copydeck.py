"""Tests for the plain-language copy deck (docs/ux-spec.md)."""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def deck():
    path = ROOT / "shell" / "copydeck.py"
    assert path.exists(), "shell/copydeck.py is missing"
    sys.path.insert(0, str(ROOT / "shell"))
    return importlib.import_module("copydeck")


def test_text_fills_in_names_from_the_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_NAME", "Matt")
    assert "Matt" in deck().text("offline")


def test_text_falls_back_when_environment_is_empty(monkeypatch):
    monkeypatch.delenv("ADMIN_NAME", raising=False)
    assert "{" not in deck().text("offline")


def test_every_key_used_by_the_airlock_exists():
    for key in ("download_safe", "download_held", "download_blocked"):
        assert key in deck().COPY, key
