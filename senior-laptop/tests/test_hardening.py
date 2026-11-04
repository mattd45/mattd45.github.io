"""Off-device checks of the hardening config files (spec 6.3)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "hardening"

SYSCTL_MIN = {
    "kernel.kptr_restrict": 1,
    "kernel.dmesg_restrict": 1,
    "kernel.unprivileged_bpf_disabled": 1,
    "kernel.kexec_load_disabled": 1,
    "kernel.sysrq": 0,
    "fs.suid_dumpable": 0,
    "net.ipv4.conf.all.accept_redirects": 0,
    "net.ipv4.conf.all.accept_source_route": 0,
    "net.ipv4.tcp_syncookies": 1,
}
BLACKLIST = ["firewire-core", "thunderbolt", "usb-storage", "uas",
             "cramfs", "freevxfs", "hfs", "hfsplus", "jffs2", "dccp", "sctp", "rds", "tipc"]
NOEXEC_MOUNTS = ["/tmp", "/home", "/var/lib/senior-laptop/quarantine"]


def read(name: str) -> list[str]:
    path = ROOT / name
    assert path.exists(), f"{name} is missing"
    return [ln.strip() for ln in path.read_text().splitlines()
            if ln.strip() and not ln.strip().startswith("#")]


def parse_sysctl() -> dict[str, str]:
    pairs = [ln.split("=", 1) for ln in read("sysctl.conf")]
    return {k.strip(): v.strip() for k, v in pairs}


def test_sysctl_values_meet_minimum():
    values = parse_sysctl()
    for key, minimum in SYSCTL_MIN.items():
        assert key in values, f"{key} not set"
        if minimum == 0:
            assert values[key] == "0", f"{key} must be 0, is {values[key]}"
        else:
            assert int(values[key]) >= minimum, f"{key} below {minimum}"


def test_sysctl_has_no_duplicate_keys():
    keys = [ln.split("=", 1)[0].strip() for ln in read("sysctl.conf")]
    assert len(keys) == len(set(keys))


def test_unused_modules_are_blocked():
    lines = read("modprobe-blacklist.conf")
    for module in BLACKLIST:
        assert f"install {module} /bin/false" in lines, f"{module} not blocked"


def test_mounts_are_noexec_nosuid_nodev():
    entries = {ln.split()[1]: ln.split()[3] for ln in read("fstab-mounts.txt")}
    for mount in NOEXEC_MOUNTS:
        assert mount in entries, f"{mount} missing from fstab-mounts.txt"
        opts = entries[mount].split(",")
        for needed in ("noexec", "nosuid", "nodev"):
            assert needed in opts, f"{mount} lacks {needed}"
