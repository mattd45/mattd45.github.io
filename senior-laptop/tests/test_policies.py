"""Off-device tests for the Firefox policy generator (spec 6.2)."""
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UBO = "uBlock0@raymondhill.net"


def rp():
    path = ROOT / "scripts" / "render_policies.py"
    assert path.exists(), "scripts/render_policies.py is missing"
    sys.path.insert(0, str(ROOT / "scripts"))
    return importlib.import_module("render_policies")


def seed_allowlist() -> list[str]:
    path = ROOT / "browser" / "allowlist.txt"
    assert path.exists(), "browser/allowlist.txt is missing"
    return rp().load_allowlist(path)


def policies() -> dict:
    return rp().render_policies(seed_allowlist())["policies"]


def test_load_allowlist_ignores_comments_and_blank_lines(tmp_path):
    f = tmp_path / "list.txt"
    f.write_text("# comment\n\nexample.com\n  *.cdn.example.com  \n")
    assert rp().load_allowlist(f) == ["example.com", "*.cdn.example.com"]


def test_seed_allowlist_covers_gmail_docs_and_facebook():
    domains = seed_allowlist()
    for needed in ("mail.google.com", "accounts.google.com", "docs.google.com",
                   "drive.google.com", "*.gstatic.com", "*.googleusercontent.com",
                   "facebook.com", "*.fbcdn.net"):
        assert needed in domains, f"{needed} missing from allowlist"


def test_everything_is_blocked_except_the_allowlist():
    p = policies()["WebsiteFilter"]
    assert p["Block"] == ["<all_urls>"]
    assert "*://mail.google.com/*" in p["Exceptions"]
    assert "*://*.fbcdn.net/*" in p["Exceptions"]
    web = [e for e in p["Exceptions"] if e.startswith("*://")]
    assert len(web) == len(seed_allowlist())


def test_only_the_downloads_folder_can_be_viewed_as_files():
    files = [e for e in policies()["WebsiteFilter"]["Exceptions"] if e.startswith("file:")]
    assert files == ["file:///home/grandma/Downloads/*"]


def test_ublock_is_forced_and_other_extensions_are_blocked():
    ext = policies()["ExtensionSettings"]
    assert ext[UBO]["installation_mode"] == "force_installed"
    assert ext["*"]["installation_mode"] == "blocked"


def test_ublock_annoyance_and_cookie_lists_are_enabled():
    lists = policies()["3rdparty"]["Extensions"][UBO]["toOverwrite"]["filterLists"]
    assert "ublock-cookies-adguard" in lists
    assert "ublock-annoyances" in lists


def test_risky_features_are_disabled():
    p = policies()
    for key in ("DisableDeveloperTools", "DisablePrivateBrowsing", "BlockAboutConfig",
                "DisableTelemetry", "DisableFormHistory", "DisableAppUpdate"):
        assert p[key] is True, key
    assert p["PasswordManagerEnabled"] is False
    assert p["PopupBlocking"]["Default"] is True
    assert p["DNSOverHTTPS"]["Enabled"] is False


def test_locked_preferences_match_the_spec():
    prefs = policies()["Preferences"]
    expected = {
        "layout.css.devPixelsPerPx": "1.3",
        "full-screen-api.enabled": False,
        "network.trr.mode": 5,
        "print.always_print_silent": True,
        "browser.sessionstore.resume_from_crash": False,
    }
    for key, value in expected.items():
        assert prefs[key]["Value"] == value, key
        assert prefs[key]["Status"] == "locked", key


def test_downloads_go_to_quarantine_without_prompting():
    p = policies()
    assert p["DownloadDirectory"] == "/var/lib/senior-laptop/quarantine"
    assert p["PromptForDownloadLocation"] is False


def test_output_is_valid_json():
    text = json.dumps(rp().render_policies(seed_allowlist()))
    assert "policies" in json.loads(text)


def test_apparmor_profile_denies_secrets_and_starts_in_complain_mode():
    path = ROOT / "browser" / "firefox.apparmor"
    assert path.exists(), "browser/firefox.apparmor is missing"
    text = path.read_text()
    assert "flags=(complain)" in text
    assert "deny /home/*/.ssh/** rwklx," in text
    assert "/var/lib/senior-laptop/quarantine/** rw," in text
