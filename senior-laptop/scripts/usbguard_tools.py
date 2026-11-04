#!/usr/bin/env python3
"""USBGuard helpers.

  usbguard generate-policy | usbguard_tools.py filter   keep only mice, keyboards, printers, hubs
  usbguard_tools.py count < rules                       number of input (HID) devices in the rules
  usbguard watch | usbguard_tools.py watch              flag when a new input device was blocked
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

KEEP = {"03", "07", "09"}   # HID (mouse, keyboard), printer, hub
_IFACE = re.compile(r"\b([0-9a-fA-F]{2}):[0-9a-fA-F]{2}:[0-9a-fA-F*]{2}\b")
_WITH = re.compile(r"with-interface\s+(?:(?:all-of|one-of|equals|equals-ordered|none-of)\s+)?(\{[^}]*\}|\S+)")


def _classes(rule: str) -> list[str]:
    match = _WITH.search(rule)
    return [c.lower() for c in _IFACE.findall(match.group(1))] if match else []


def filter_rules(text: str, keep: set[str] = KEEP) -> str:
    kept = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("allow "):
            continue
        classes = _classes(line)
        if classes and all(c in keep for c in classes):
            kept.append(line)
    return "".join(f"{line}\n" for line in kept)


def count_input_devices(rules: str) -> int:
    return sum(1 for line in rules.splitlines() if line.startswith("allow ") and (c := _classes(line)) and set(c) == {"03"})


class UsbWatchParser:
    """Reads `usbguard watch` output line by line; feed() is True once a blocked input device is seen."""

    def __init__(self) -> None:
        self._insert = False
        self._blocked = False

    def feed(self, line: str) -> bool:
        line = line.strip()
        if line.startswith("[device] PresenceChanged"):
            self._insert = self._blocked = False
        elif line.startswith("event="):
            self._insert = line == "event=Insert"
        elif line.startswith("target="):
            self._blocked = line == "target=block"
        elif line.startswith("device_rule="):
            return self._insert and self._blocked and "03" in _classes(line)
        return False


def main(argv: list[str]) -> int:
    mode = argv[1] if len(argv) > 1 else ""
    if mode == "filter":
        sys.stdout.write(filter_rules(sys.stdin.read()))
    elif mode == "count":
        print(count_input_devices(sys.stdin.read()))
    elif mode == "watch":
        flag = Path(os.environ.get("SENIOR_USB_FLAG", "/run/senior-laptop/usb-blocked"))
        parser = UsbWatchParser()
        for line in sys.stdin:
            if parser.feed(line):
                flag.parent.mkdir(parents=True, exist_ok=True)
                flag.write_text("1")
    else:
        print(__doc__, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
