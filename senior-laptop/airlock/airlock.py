#!/usr/bin/env python3
"""Download airlock (spec 6.6): quarantine -> type check + ClamAV scan -> Downloads.

Usage: airlock.py [--once] QUARANTINE_DIR DOWNLOADS_DIR
Never delivers a file it has not scanned; the bytes scanned are the bytes delivered.
"""
from __future__ import annotations

import enum
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shell"))
from copydeck import text  # noqa: E402

log = logging.getLogger("airlock")
RETRY_SECONDS = 300
PARTIAL_SUFFIXES = (".part", ".tmp", ".crdownload")
MAX_SIGNATURE_AGE_SECONDS = 3 * 86400
EXTENSIONS = {"pdf": {".pdf"}, "doc": {".doc"}, "docx": {".docx"}, "jpg": {".jpg", ".jpeg"},
              "png": {".png"}, "txt": {".txt"}}
ALLOWED_MIME = {
    "application/pdf": "pdf",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "image/jpeg": "jpg",
    "image/png": "png",
    "text/plain": "txt",
}


class Verdict(enum.Enum):
    CLEAN = "clean"
    INFECTED = "infected"
    BLOCKED_TYPE = "blocked_type"
    SCAN_ERROR = "scan_error"
    INCOMPLETE = "incomplete"


def classify(path: Path) -> str | None:
    """Allowed type name from the file's content (libmagic), never its extension."""
    try:
        out = subprocess.run(["file", "--mime-type", "-b", str(path)],
                             capture_output=True, text=True, timeout=30, check=True)
    except (OSError, subprocess.SubprocessError):
        return None
    return ALLOWED_MIME.get(out.stdout.strip())


def signatures_fresh(clamav_dir: Path | None = None, now: Callable[[], float] = time.time) -> bool:
    """False if the virus signatures are missing or older than three days (fail closed)."""
    directory = Path(clamav_dir or os.environ.get("AIRLOCK_CLAMAV_DIR", "/var/lib/clamav"))
    if not directory.is_dir():
        return True                       # nothing to judge here; clamdscan reports its own errors
    daily = list(directory.glob("daily.c[vl]d"))
    return bool(daily) and now() - max(p.stat().st_mtime for p in daily) <= MAX_SIGNATURE_AGE_SECONDS


def _final_name(name: str, kind: str) -> str:
    """Delivered files always carry an extension that matches their detected type."""
    return name if Path(name).suffix.lower() in EXTENSIONS[kind] else f"{name}.{kind}"


def scan(path: Path, clamdscan: str | None = None, clamav_dir: Path | None = None) -> Verdict:
    if not signatures_fresh(clamav_dir):
        return Verdict.SCAN_ERROR
    clamdscan = clamdscan or os.environ.get("AIRLOCK_CLAMDSCAN", "clamdscan")
    try:
        rc = subprocess.run([clamdscan, "--fdpass", "--no-summary", str(path)],
                            capture_output=True, timeout=120).returncode
    except (OSError, subprocess.SubprocessError):
        return Verdict.SCAN_ERROR
    return {0: Verdict.CLEAN, 1: Verdict.INFECTED}.get(rc, Verdict.SCAN_ERROR)


def alert_admin(message: str) -> None:
    helper = os.environ.get("SENIOR_ALERT", "/usr/local/bin/senior-laptop-alert")
    if Path(helper).exists():
        try:
            subprocess.run([helper, message], timeout=30, check=False)
            return
        except (OSError, subprocess.SubprocessError) as exc:
            log.warning("alert helper failed: %s", exc)
    log.warning("ADMIN ALERT: %s", message)


def notify_user(message: str) -> None:
    """Drop a message file in the spool the shell turns into a large on-screen message."""
    spool = Path(os.environ.get("SENIOR_MESSAGES", "/run/senior-laptop/messages"))
    try:
        spool.mkdir(parents=True, exist_ok=True)
        os.chmod(spool, 0o755)
        target = spool / f"{time.time_ns()}.txt"
        target.write_text(message)
        os.chmod(target, 0o644)
        for old in spool.glob("*.txt"):            # prune anything older than an hour
            if time.time() - old.stat().st_mtime > 3600:
                old.unlink(missing_ok=True)
    except OSError as exc:
        log.warning("could not write user message: %s", exc)


def default_notify(audience: str, message: str) -> None:
    (alert_admin if audience == "admin" else notify_user)(message)


def _unique(dest: Path) -> Path:
    if not dest.exists():
        return dest
    n = 1
    while (cand := dest.with_name(f"{dest.stem} ({n}){dest.suffix}")).exists():
        n += 1
    return cand


def process(path: Path, downloads_dir: Path, notify: Callable[[str, str], None],
            scan_fn: Callable[[Path], Verdict] = scan, settle: float = 1.0,
            sleep: Callable[[float], None] = time.sleep) -> Verdict:
    path, downloads_dir = Path(path), Path(downloads_dir)
    name = path.name
    if not path.is_file() or name.startswith(".") or name.endswith(PARTIAL_SUFFIXES):
        return Verdict.INCOMPLETE
    size = path.stat().st_size
    if size == 0:
        return Verdict.INCOMPLETE
    if settle:
        sleep(settle)
        if not path.is_file() or path.stat().st_size != size:
            return Verdict.INCOMPLETE

    with tempfile.TemporaryDirectory(prefix="airlock-") as stage:
        staged = Path(stage) / name
        shutil.copyfile(path, staged)               # scan and deliver this private copy

        kind = classify(staged)
        if kind is None:
            path.unlink(missing_ok=True)
            notify("admin", f"Removed a disallowed file type: {name}")
            notify("user", text("download_blocked"))
            return Verdict.BLOCKED_TYPE

        verdict = scan_fn(staged)
        if verdict is Verdict.INFECTED:
            path.unlink(missing_ok=True)
            notify("admin", f"Removed an infected download: {name}")
            notify("user", text("download_blocked"))
        elif verdict is Verdict.CLEAN:
            dest = _unique(downloads_dir / _final_name(name, kind))
            tmp = downloads_dir / f".{dest.name}.partial"
            shutil.copyfile(staged, tmp)
            os.chmod(tmp, 0o644)
            os.replace(tmp, dest)
            path.unlink(missing_ok=True)
            notify("user", text("download_safe"))
        else:
            verdict = Verdict.SCAN_ERROR
            notify("admin", f"Scanner unavailable; holding download: {name}")
            notify("user", text("download_held"))
        return verdict


@dataclass
class SweepState:
    held_until: dict[str, float] = field(default_factory=dict)
    notified: set[str] = field(default_factory=set)


def sweep(quarantine: Path, downloads_dir: Path, notify: Callable[[str, str], None],
          scan_fn: Callable[[Path], Verdict] = scan, settle: float = 1.0,
          sleep: Callable[[float], None] = time.sleep,
          now: Callable[[], float] = time.monotonic,
          state: SweepState | None = None) -> dict[str, Verdict]:
    """Process every file in quarantine; retry held files quietly every RETRY_SECONDS."""
    state = state or SweepState()
    quiet = lambda audience, message: None  # noqa: E731
    results: dict[str, Verdict] = {}
    for path in sorted(Path(quarantine).iterdir()):
        if now() < state.held_until.get(path.name, 0):
            continue
        try:
            verdict = process(path, downloads_dir, quiet if path.name in state.notified else notify,
                              scan_fn=scan_fn, settle=settle, sleep=sleep)
        except Exception as exc:  # noqa: BLE001 - one bad file must never stop the airlock
            log.exception("airlock error on %s", path.name)
            verdict = Verdict.SCAN_ERROR
            if path.name not in state.notified:
                notify("admin", f"Airlock error on {path.name}: {exc}")
                notify("user", text("download_held"))
        results[path.name] = verdict
        if verdict is Verdict.SCAN_ERROR:
            state.held_until[path.name] = now() + RETRY_SECONDS
            state.notified.add(path.name)
        else:
            state.held_until.pop(path.name, None)
            state.notified.discard(path.name)
    return results


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--once"]
    once = "--once" in argv
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    quarantine, downloads = Path(args[0]), Path(args[1])
    state = SweepState()
    while True:
        sweep(quarantine, downloads, default_notify, state=state)
        if once:
            return 0
        subprocess.run(["inotifywait", "-q", "-t", "30", "-e", "close_write", "-e", "moved_to",
                        str(quarantine)], check=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    sys.exit(main(sys.argv[1:]))
