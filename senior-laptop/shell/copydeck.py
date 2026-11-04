"""Plain-language copy deck: the only place user-facing text lives (docs/ux-spec.md).

Named copydeck (not copy) so it never shadows Python's standard library `copy` module.
Wording is DRAFT until confirmed with her (plan Task 1b).
"""
import os
from collections import defaultdict

COPY = {
    "offline": "The internet isn't connected. Tap Help and {ADMIN_NAME} will sort it out.",
    "printer_paper_ink": "The printer needs paper or ink. Ask {ADMIN_NAME}.",
    "printer_offline": "The printer is switched off. Please switch it on.",
    "new_device_blocked": "A new device was blocked. Ask {ADMIN_NAME}.",
    "download_safe": "Checked and safe.",
    "download_held": "I couldn't check that file yet. Ask {ADMIN_NAME}.",
    "download_blocked": "That file isn't allowed, so it was removed.",
    "downloads_empty": "No files yet.",
    "print_sent": "Sent to the printer.",
    "turn_off_confirm": "Turn off the computer?",
    "turn_off_yes": "Turn off",
    "turn_off_no": "Keep working",
    "help_title": "Need help? Call {ADMIN_NAME}",
    "connected_for_support": "{ADMIN_NAME} can see this computer if you ask.",
    "block_page": "That page isn't available. Tap Help and {ADMIN_NAME} will sort it out.",
}

_FALLBACKS = {"ADMIN_NAME": "your helper", "ADMIN_PHONE": "", "HER_NAME": "there"}


def text(key: str, **extra: str) -> str:
    """Return COPY[key] with {ADMIN_NAME}, {ADMIN_PHONE}, {HER_NAME} filled in."""
    values = defaultdict(str, {k: os.environ.get(k) or v for k, v in _FALLBACKS.items()})
    values.update(extra)
    return COPY[key].format_map(values)
