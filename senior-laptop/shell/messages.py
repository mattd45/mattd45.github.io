"""Plain-language status messages for the shell. No GTK imports."""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path

from copydeck import text

USB_FLAG = Path("/run/senior-laptop/usb-blocked")
SPOOL = Path("/run/senior-laptop/messages")


def _online() -> bool:
    try:
        socket.create_connection(("9.9.9.9", 443), timeout=2).close()
        return True
    except OSError:
        return False


def connectivity_message(probe=_online) -> str | None:
    return None if probe() else text("offline")


def parse_alerts(output: str) -> list[str]:
    """Pull the CUPS 'Alerts:' reasons out of `lpstat -l -p` output."""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("Alerts:"):
            value = stripped[len("Alerts:"):].strip()
            return [] if value in ("", "none") else value.split()
    return []


def cups_alerts() -> list[str]:
    try:
        out = subprocess.run(["lpstat", "-l", "-p"], capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return []
    return parse_alerts(out.stdout)


def printer_message(alerts=cups_alerts) -> str | None:
    found = alerts()
    if any(a.startswith(("offline", "shutdown", "connecting-to-device", "disconnected")) for a in found):
        return text("printer_offline")
    if any(a.startswith(("media-", "toner-", "marker-supply", "ink-")) for a in found):
        return text("printer_paper_ink")
    return None


def usb_blocked_message(flag: Path = USB_FLAG) -> str | None:
    return text("new_device_blocked") if Path(flag).exists() else None


def read_new_messages(spool: Path, seen: set[str]) -> list[str]:
    """Messages dropped by the airlock (and others), oldest first, each returned once."""
    spool = Path(spool)
    if not spool.is_dir():
        return []
    fresh = []
    for path in sorted(spool.glob("*.txt")):
        if path.name in seen:
            continue
        seen.add(path.name)
        try:
            fresh.append(path.read_text())
        except OSError:
            continue
    return fresh
