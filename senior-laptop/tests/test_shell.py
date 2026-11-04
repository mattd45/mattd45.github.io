"""Off-device tests for the shell's logic (spec section 7). GTK files only get syntax-checked here."""
import importlib
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHELL = ROOT / "shell"


def mod(name):
    path = SHELL / f"{name}.py"
    assert path.exists(), f"shell/{name}.py is missing"
    if str(SHELL) not in sys.path:
        sys.path.insert(0, str(SHELL))
    return importlib.import_module(name)


# ---- tiles ----
def test_tiles_are_exactly_the_five_in_order():
    tiles = mod("core").load_tiles(SHELL / "tiles.json")
    assert [t.label for t in tiles] == ["Email", "Facebook", "Write a Letter", "My Downloads", "Help"]
    assert all(t.command and t.icon for t in tiles)


def test_email_and_letter_share_the_google_profile_and_facebook_has_its_own():
    cmds = {t.label: t.command for t in mod("core").load_tiles(SHELL / "tiles.json")}
    assert "google" in cmds["Email"] and "google" in cmds["Write a Letter"]
    assert "facebook" in cmds["Facebook"] and "google" not in cmds["Facebook"]
    assert all("--kiosk" in cmds[k] for k in ("Email", "Facebook", "Write a Letter"))


# ---- click debounce ----
def test_second_click_inside_the_window_is_ignored():
    d = mod("core").ClickDebouncer()
    assert d.accept(0) is True
    assert d.accept(300) is False
    assert d.accept(700) is True


def test_ignored_clicks_do_not_extend_the_window():
    d = mod("core").ClickDebouncer(window_ms=600)
    d.accept(0); d.accept(500); d.accept(550)
    assert d.accept(650) is True


# ---- orientation text ----
def test_greeting_follows_the_time_of_day():
    greeting = mod("core").greeting
    assert greeting(datetime(2026, 11, 4, 9, 0), "Ann") == "Good morning, Ann"
    assert greeting(datetime(2026, 11, 4, 14, 0), "Ann") == "Good afternoon, Ann"
    assert greeting(datetime(2026, 11, 4, 20, 0), "Ann") == "Good evening, Ann"


def test_date_and_clock_are_plain():
    core = mod("core")
    now = datetime(2026, 11, 4, 15, 5)
    assert core.date_text(now) == "Wednesday 4 November"
    assert core.clock_text(now) == "3:05 PM"


# ---- messages ----
def test_offline_message_only_when_not_connected(monkeypatch):
    m = mod("messages")
    monkeypatch.setenv("ADMIN_NAME", "Matt")
    assert m.connectivity_message(probe=lambda: True) is None
    assert "Matt" in m.connectivity_message(probe=lambda: False)


def test_printer_alerts_map_to_plain_messages():
    m = mod("messages")
    assert m.printer_message(alerts=lambda: []) is None
    assert "paper or ink" in m.printer_message(alerts=lambda: ["media-empty-error"])
    assert "paper or ink" in m.printer_message(alerts=lambda: ["marker-supply-low-warning"])
    assert "switched off" in m.printer_message(alerts=lambda: ["offline-report"])


def test_lpstat_output_is_parsed_into_alerts():
    parse = mod("messages").parse_alerts
    assert parse("printer Home is idle.\n\tAlerts: none\n") == []
    assert parse("printer Home is idle.\n\tAlerts: media-empty-error media-needed-report\n") == [
        "media-empty-error", "media-needed-report"]


def test_blocked_usb_message_follows_the_flag_file(tmp_path):
    m = mod("messages")
    flag = tmp_path / "usb-blocked"
    assert m.usb_blocked_message(flag=flag) is None
    flag.write_text("1")
    assert m.usb_blocked_message(flag=flag) is not None


def test_new_spool_messages_are_returned_once_in_order(tmp_path):
    m = mod("messages")
    (tmp_path / "2.txt").write_text("second")
    (tmp_path / "1.txt").write_text("first")
    (tmp_path / "ignore.log").write_text("nope")
    seen: set[str] = set()
    assert m.read_new_messages(tmp_path, seen) == ["first", "second"]
    assert m.read_new_messages(tmp_path, seen) == []
    (tmp_path / "3.txt").write_text("third")
    assert m.read_new_messages(tmp_path, seen) == ["third"]


# ---- help screen ----
def test_help_lines_show_name_phone_and_support_status(monkeypatch):
    core = mod("core")
    monkeypatch.setenv("ADMIN_NAME", "Matt"); monkeypatch.setenv("ADMIN_PHONE", "07700 900123")
    connected = core.help_lines(connected=True)
    assert connected[0] == "Need help? Call Matt" and "07700 900123" in connected
    assert any("can see this computer" in ln for ln in connected)
    assert not any("can see this computer" in ln for ln in core.help_lines(connected=False))


# ---- compositor config ----
def test_sway_config_has_no_chrome_and_removes_closing_shortcuts():
    path = SHELL / "sway.conf"
    assert path.exists(), "shell/sway.conf is missing"
    lines = [ln.strip().lower() for ln in path.read_text().splitlines() if not ln.strip().startswith("#")]
    text = "\n".join(lines)
    assert "default_border none" in text and "focus_follows_mouse no" in text
    for key in ("ctrl+w", "ctrl+q", "alt+f4", "f11", "ctrl+t", "ctrl+n"):
        assert f"bindsym {key} nop" in text, key
    for banned in ("terminal", "xterm", "foot", "alacritty", "bindsym mod4"):
        assert banned not in text, banned


# ---- environment file and support status ----
def test_env_file_is_read_without_overriding_real_environment(tmp_path, monkeypatch):
    core = mod("core")
    f = tmp_path / "env"
    f.write_text('# comment\nADMIN_NAME="Matt"\nHER_NAME=Ann\n\nADMIN_PHONE="07700 900123"\n')
    monkeypatch.delenv("ADMIN_NAME", raising=False)
    monkeypatch.setenv("HER_NAME", "Already")
    core.load_env_file(f)
    import os
    assert os.environ["ADMIN_NAME"] == "Matt" and os.environ["HER_NAME"] == "Already"
    assert os.environ["ADMIN_PHONE"] == "07700 900123"


def test_support_is_connected_only_when_tailscale_is_running():
    core = mod("core")

    class Result:
        def __init__(self, out): self.stdout = out

    assert core.support_connected(run=lambda *a, **k: Result('{"BackendState": "Running"}')) is True
    assert core.support_connected(run=lambda *a, **k: Result('{"BackendState": "Stopped"}')) is False

    def boom(*a, **k): raise OSError("no tailscale")
    assert core.support_connected(run=boom) is False


# ---- theme sizes (spec 7.1 rule 1) ----
def test_theme_meets_the_minimum_sizes():
    import re
    path = SHELL / "theme.css"
    assert path.exists(), "shell/theme.css is missing"
    css = path.read_text()
    sizes = [int(m) for m in re.findall(r"font-size:\s*(\d+)px", css)]
    assert sizes and min(sizes) >= 28, sizes
    assert 40 in sizes or max(sizes) >= 40
    heights = [int(m) for m in re.findall(r"min-height:\s*(\d+)px", css)]
    assert heights and min(heights) >= 72, heights


# ---- review fixes ----
def test_turn_off_confirmation_ignores_clicks_until_it_has_been_on_screen_a_moment():
    guard = mod("core").DelayedConfirm(delay_ms=1000)
    assert guard.accept(0) is False                 # never shown
    guard.shown(5000)
    assert guard.accept(5300) is False              # the second click of a double-click
    assert guard.accept(6100) is True


class FakeProc:
    def __init__(self, hang=False):
        self.hang, self.calls, self._done = hang, [], False

    def poll(self):
        return 0 if self._done else None

    def terminate(self):
        self.calls.append("terminate")

    def kill(self):
        self.calls.append("kill"); self._done = True

    def wait(self, timeout=None):
        self.calls.append("wait")
        if self.hang and not self._done:
            import subprocess
            raise subprocess.TimeoutExpired("fake", timeout)
        self._done = True


def test_stop_process_waits_for_a_graceful_exit_then_kills_if_it_hangs():
    core = mod("core")
    graceful = FakeProc()
    core.stop_process(graceful, timeout=0.1)
    assert graceful.calls == ["terminate", "wait"]
    stuck = FakeProc(hang=True)
    core.stop_process(stuck, timeout=0.1)
    assert stuck.calls == ["terminate", "wait", "kill", "wait"]
    core.stop_process(None)                          # nothing running: fine


def test_downloads_list_is_newest_first_and_hides_dotfiles(tmp_path):
    import os
    core = mod("core")
    for name, age in (("old.pdf", 300), ("new.pdf", 10), (".hidden.partial", 5)):
        f = tmp_path / name; f.write_text("x")
        os.utime(f, (f.stat().st_mtime - age, f.stat().st_mtime - age))
    (tmp_path / "folder").mkdir()
    assert [p.name for p in core.list_downloads(tmp_path)] == ["new.pdf", "old.pdf"]
    assert core.list_downloads(tmp_path / "missing") == []


def test_sway_restarts_the_shell_if_it_ever_exits():
    text = (SHELL / "sway.conf").read_text()
    exec_lines = [ln for ln in text.splitlines() if ln.strip().startswith("exec ")]
    assert any("while" in ln and "shell.py" in ln for ln in exec_lines)


def test_bottom_bar_is_drawn_above_fullscreen_browser_windows():
    source = (SHELL / "shell.py").read_text()
    assert "set_layer(self.bar, GtkLayerShell.Layer.OVERLAY)" in source
