"""Tests for the fstab editor that replaced inline awk (review: the /home line could make the laptop unbootable)."""
import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

FSTAB = """# /etc/fstab
UUID=abc / btrfs subvol=@rootfs,compress=zstd 0 0
UUID=abc /home btrfs subvol=@home,compress=zstd 0 0
UUID=def /boot ext4 defaults 0 2
"""
TEMPLATE = """# template
tmpfs /tmp tmpfs size=1G,noexec,nosuid,nodev 0 0
@KEEP@ /home btrfs noexec,nosuid,nodev 0 0
tmpfs /home/grandma/.cache tmpfs uid=@GRANDMA_UID@,gid=@GRANDMA_UID@,noexec 0 0
"""


def ft():
    path = ROOT / "scripts" / "fstab_tools.py"
    assert path.exists(), "scripts/fstab_tools.py is missing"
    sys.path.insert(0, str(ROOT / "scripts"))
    return importlib.import_module("fstab_tools")


def lines(text):
    return {ln.split()[1]: ln.split() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")}


def test_home_keeps_its_device_and_existing_options_and_gains_the_hardening_options():
    out = lines(ft().apply_fstab(TEMPLATE, FSTAB, "abc", "1001"))
    home = out["/home"]
    assert home[0] == "UUID=abc" and home[2] == "btrfs"
    opts = home[3].split(",")
    assert {"subvol=@home", "compress=zstd", "noexec", "nosuid", "nodev"} <= set(opts)


def test_new_mounts_are_appended_with_the_uid_filled_in_and_other_lines_untouched():
    out = lines(ft().apply_fstab(TEMPLATE, FSTAB, "abc", "1001"))
    assert out["/tmp"][2] == "tmpfs"
    assert "uid=1001" in out["/home/grandma/.cache"][3]
    assert out["/boot"][0] == "UUID=def" and out["/"][3] == "subvol=@rootfs,compress=zstd"


def test_applying_twice_changes_nothing():
    once = ft().apply_fstab(TEMPLATE, FSTAB, "abc", "1001")
    assert ft().apply_fstab(TEMPLATE, once, "abc", "1001") == once


def test_refuses_when_there_is_no_home_entry_to_harden():
    no_home = "\n".join(ln for ln in FSTAB.splitlines() if " /home " not in ln) + "\n"
    with pytest.raises(ValueError):
        ft().apply_fstab(TEMPLATE, no_home, "abc", "1001")
