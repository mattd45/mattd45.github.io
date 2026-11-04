"""Shell logic with no GTK imports, so it can be tested anywhere (spec section 7)."""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from copydeck import text


@dataclass(frozen=True)
class Tile:
    label: str
    command: list[str]
    icon: str


def load_tiles(path: Path) -> list[Tile]:
    return [Tile(t["label"], list(t["command"]), t["icon"]) for t in json.loads(Path(path).read_text())]


class ClickDebouncer:
    """Ignore a second click inside the window (a Windows-style double-click does one thing)."""

    def __init__(self, window_ms: int = 600) -> None:
        self.window_ms = window_ms
        self._last: int | None = None

    def accept(self, now_ms: int) -> bool:
        if self._last is not None and now_ms - self._last < self.window_ms:
            return False
        self._last = now_ms
        return True


def greeting(now: datetime, name: str) -> str:
    part = "morning" if now.hour < 12 else "afternoon" if now.hour < 18 else "evening"
    return f"Good {part}, {name}"


def date_text(now: datetime) -> str:
    return f"{now:%A} {now.day} {now:%B}"


def clock_text(now: datetime) -> str:
    return f"{now.hour % 12 or 12}:{now.minute:02d} {'AM' if now.hour < 12 else 'PM'}"


def help_lines(connected: bool) -> list[str]:
    lines = [text("help_title")]
    phone = os.environ.get("ADMIN_PHONE", "")
    if phone:
        lines.append(phone)
    if connected:
        lines.append(text("connected_for_support"))
    return lines


def load_env_file(path: Path) -> None:
    """Read KEY=value lines (optionally quoted) into os.environ without overriding real values."""
    try:
        content = Path(path).read_text()
    except OSError:
        return
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def support_connected(run=subprocess.run) -> bool:
    try:
        out = run(["tailscale", "status", "--json"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return False
    return '"BackendState": "Running"' in out.stdout


class DelayedConfirm:
    """A confirmation that ignores clicks until it has been on screen for a moment, so the
    second click of a double-click can never confirm it."""

    def __init__(self, delay_ms: int = 1000) -> None:
        self.delay_ms = delay_ms
        self._shown: int | None = None

    def shown(self, now_ms: int) -> None:
        self._shown = now_ms

    def accept(self, now_ms: int) -> bool:
        return self._shown is not None and now_ms - self._shown >= self.delay_ms


def stop_process(proc, timeout: float = 5.0) -> None:
    """Ask an app to quit, wait for it, and kill it if it hangs (so the next launch of the same
    Firefox profile never meets a half-closed one)."""
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()


def list_downloads(directory: Path) -> list[Path]:
    """Her delivered files, newest first, without hidden or partial leftovers."""
    directory = Path(directory)
    if not directory.is_dir():
        return []
    files = [p for p in directory.iterdir() if p.is_file() and not p.name.startswith(".")]
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)
