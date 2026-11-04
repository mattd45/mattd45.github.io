#!/usr/bin/env python3
"""Apply hardening/fstab-mounts.txt to an fstab.

Usage: fstab_tools.py TEMPLATE FSTAB ROOT_UUID GRANDMA_UID > new-fstab

Template lines replace or append a mount. A line starting with @KEEP@ keeps the existing entry's
device, type and options and only ADDS the template's options (used for /home, so an existing
layout is never replaced); it is an error if there is no such entry.
"""
from __future__ import annotations

import sys
from pathlib import Path


def apply_fstab(template: str, fstab: str, uuid: str, guid: str) -> str:
    out = fstab.splitlines()

    def find(mountpoint: str) -> int | None:
        for i, line in enumerate(out):
            fields = line.split()
            if len(fields) > 1 and not fields[0].startswith("#") and fields[1] == mountpoint:
                return i
        return None

    for raw in template.splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        entry = raw.replace("@ROOTUUID@", uuid).replace("@GRANDMA_UID@", guid)
        fields = entry.split()
        mountpoint, index = fields[1], find(fields[1])
        if fields[0] == "@KEEP@":
            if index is None:
                raise ValueError(f"{mountpoint} is not in /etc/fstab; refusing to guess its device")
            current = out[index].split()
            options = current[3].split(",")
            options += [o for o in fields[3].split(",") if o not in options]
            current[3] = ",".join(options)
            out[index] = " ".join(current)
        elif index is None:
            out.append(entry)
        else:
            out[index] = entry
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        sys.stdout.write(apply_fstab(Path(argv[1]).read_text(), Path(argv[2]).read_text(), argv[3], argv[4]))
    except ValueError as exc:
        print(f"fstab_tools: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
