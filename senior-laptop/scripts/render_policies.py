#!/usr/bin/env python3
"""Render the Firefox ESR enterprise policy file from browser/allowlist.txt.

Usage: render_policies.py ALLOWLIST OUTPUT_JSON
"""
import json
import sys
from pathlib import Path

UBO = "uBlock0@raymondhill.net"
QUARANTINE = "/var/lib/senior-laptop/quarantine"
DOWNLOADS_VIEW = "file:///home/grandma/Downloads/*"   # lets the Downloads viewer open PDFs and images
UBO_LISTS = ["user-filters", "ublock-filters", "ublock-badware", "ublock-unbreak",
             "easylist", "ublock-cookies-adguard", "ublock-annoyances"]


def load_allowlist(path: Path) -> list[str]:
    """One domain per line; blank lines and '#' comments are ignored."""
    lines = (ln.strip() for ln in Path(path).read_text().splitlines())
    return [ln for ln in lines if ln and not ln.startswith("#")]


def _pref(value):
    return {"Value": value, "Status": "locked"}


def render_policies(allowlist: list[str]) -> dict:
    return {"policies": {
        "WebsiteFilter": {
            "Block": ["<all_urls>"],
            "Exceptions": [f"*://{domain}/*" for domain in allowlist] + [DOWNLOADS_VIEW],
        },
        "ExtensionSettings": {
            UBO: {
                "installation_mode": "force_installed",
                "install_url": "https://addons.mozilla.org/firefox/downloads/latest/ublock-origin/latest.xpi",
            },
            "*": {"installation_mode": "blocked"},
        },
        "3rdparty": {"Extensions": {UBO: {"toOverwrite": {"filterLists": UBO_LISTS}}}},
        "DisableDeveloperTools": True,
        "DisablePrivateBrowsing": True,
        "BlockAboutConfig": True,
        "BlockAboutProfiles": True,
        "BlockAboutSupport": True,
        "DisableTelemetry": True,
        "DisableFirefoxStudies": True,
        "DisablePocket": True,
        "DisableFormHistory": True,
        "DisableAppUpdate": True,
        "DisableProfileImport": True,
        "DontCheckDefaultBrowser": True,
        "NoDefaultBookmarks": True,
        "PasswordManagerEnabled": False,
        "OfferToSaveLogins": False,
        "AutofillAddressEnabled": False,
        "AutofillCreditCardEnabled": False,
        "PopupBlocking": {"Default": True, "Locked": True},
        "Notifications": {"BlockNewRequests": True, "Locked": True},
        "Permissions": {
            "Camera": {"BlockNewRequests": True, "Locked": True},
            "Microphone": {"BlockNewRequests": True, "Locked": True},
            "Location": {"BlockNewRequests": True, "Locked": True},
        },
        "DNSOverHTTPS": {"Enabled": False, "Locked": True},
        "OverrideFirstRunPage": "",
        "OverridePostUpdatePage": "",
        "UserMessaging": {"WhatsNew": False, "ExtensionRecommendations": False,
                          "FeatureRecommendations": False, "UrlbarInterventions": False,
                          "SkipOnboarding": True, "MoreFromMozilla": False},
        "DownloadDirectory": QUARANTINE,
        "PromptForDownloadLocation": False,
        "Preferences": {
            "layout.css.devPixelsPerPx": _pref("1.3"),
            "full-screen-api.enabled": _pref(False),
            "network.trr.mode": _pref(5),
            "print.always_print_silent": _pref(True),
            "browser.sessionstore.resume_from_crash": _pref(False),
            "browser.tabs.warnOnClose": _pref(False),
            "dom.disable_beforeunload": _pref(True),
            "media.autoplay.default": _pref(5),
        },
    }}


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    policies = render_policies(load_allowlist(Path(argv[1])))
    Path(argv[2]).write_text(json.dumps(policies, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
