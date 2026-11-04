#!/usr/bin/env python3
"""The custom shell: Home screen, bottom bar and messages (spec section 7).

Needs GTK 3 and gtk-layer-shell; runs inside the locked-down sway session. Logic lives in
core.py and messages.py (tested off-device); this file only wires widgets to it.
"""
import os
import signal
import subprocess
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import gi  # noqa: E402

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gdk, GLib, Gtk, GtkLayerShell  # noqa: E402

import core  # noqa: E402
import messages  # noqa: E402
from copydeck import text  # noqa: E402

core.load_env_file(Path("/etc/senior-laptop.env"))
DOWNLOADS = Path(os.environ.get("SENIOR_DOWNLOADS", "/home/grandma/Downloads"))


def big_button(label, css_class=None):
    button = Gtk.Button(label=label)
    if css_class:
        button.get_style_context().add_class(css_class)
    return button


class Toast(Gtk.Window):
    """A large, calm message at the top of the screen. Goes away on click or after 10 seconds."""

    def __init__(self, message):
        super().__init__()
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 40)
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.get_style_context().add_class("toast")
        label = Gtk.Label(label=message)
        label.set_line_wrap(True)
        ok = big_button("OK")
        ok.connect("clicked", lambda _b: self.destroy())
        box.pack_start(label, True, True, 0)
        box.pack_start(ok, False, False, 0)
        self.add(box)
        self.show_all()
        GLib.timeout_add_seconds(10, self._expire)

    def _expire(self):
        self.destroy()
        return False


class Shell:
    def __init__(self):
        self.tiles = core.load_tiles(HERE / "tiles.json")
        self.debounce = core.ClickDebouncer()
        self.app = None
        self.seen_messages = set()
        self.active_alerts = set()
        self._build_main()
        self._build_bar()
        self._tick()          # after both windows exist: it updates the greeting and the bar clock
        GLib.timeout_add_seconds(1, self._tick)
        GLib.timeout_add_seconds(2, self._poll_spool)
        GLib.timeout_add_seconds(20, self._poll_status)

    # ---- windows ----
    def _build_main(self):
        self.main = Gtk.Window()
        self.main.set_decorated(False)
        self.main.maximize()
        self.stack = Gtk.Stack()
        self.main.add(self.stack)
        self._build_home()
        self.stack.add_named(Gtk.Box(), "help")
        self.stack.add_named(Gtk.Box(), "downloads")
        self.stack.add_named(self._turn_off_page(), "turnoff")
        self.main.show_all()

    def _page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        box.set_border_width(40)
        box.get_style_context().add_class("page")
        return box

    def _build_home(self):
        page = self._page()
        self.greeting = Gtk.Label()
        self.greeting.get_style_context().add_class("greeting")
        self.datetime = Gtk.Label()
        self.datetime.get_style_context().add_class("datetime")
        page.pack_start(self.greeting, False, False, 0)
        page.pack_start(self.datetime, False, False, 0)
        grid = Gtk.Grid(column_spacing=24, row_spacing=24, halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        for index, tile in enumerate(self.tiles):
            button = big_button(f"{tile.icon}\n{tile.label}", "tile")
            button.connect("clicked", self._on_tile, tile)
            grid.attach(button, index % 3, index // 3, 1, 1)
        off = big_button("Turn off", "danger")
        off.connect("clicked", lambda _b: self.stack.set_visible_child_name("turnoff"))
        grid.attach(off, 2, 1, 1, 1)
        page.pack_start(grid, True, True, 0)
        self.stack.add_named(page, "home")

    def _turn_off_page(self):
        page = self._page()
        page.pack_start(Gtk.Label(label=text("turn_off_confirm")), True, True, 0)
        keep = big_button(text("turn_off_no"), "danger")
        keep.connect("clicked", lambda _b: self.go_home())
        yes = big_button(text("turn_off_yes"), "danger")
        yes.connect("clicked", lambda _b: subprocess.Popen(["systemctl", "poweroff"]))
        page.pack_start(keep, False, False, 0)   # "Keep working" comes first and is the default
        page.pack_start(yes, False, False, 0)
        return page

    def _build_bar(self):
        self.bar = Gtk.Window()
        GtkLayerShell.init_for_window(self.bar)
        GtkLayerShell.set_layer(self.bar, GtkLayerShell.Layer.TOP)
        for edge in (GtkLayerShell.Edge.BOTTOM, GtkLayerShell.Edge.LEFT, GtkLayerShell.Edge.RIGHT):
            GtkLayerShell.set_anchor(self.bar, edge, True)
        GtkLayerShell.auto_exclusive_zone_enable(self.bar)
        GtkLayerShell.set_keyboard_mode(self.bar, GtkLayerShell.KeyboardMode.NONE)
        box = Gtk.Box(spacing=6)
        box.get_style_context().add_class("bar")
        for label, handler in (("Home", self.go_home), ("Back", self.back), ("Print", self.print_page),
                               ("Volume -", lambda: self.volume("5%-")), ("Volume +", lambda: self.volume("5%+")),
                               ("Help", self.show_help)):
            button = big_button(label)
            button.connect("clicked", lambda _b, h=handler: h())
            box.pack_start(button, False, False, 0)
        self.clock = Gtk.Label()
        self.clock.get_style_context().add_class("clock")
        box.pack_end(self.clock, False, False, 0)
        self.bar.add(box)
        self.bar.show_all()

    # ---- behaviour ----
    def _tick(self):
        now = datetime.now()
        self.greeting.set_text(core.greeting(now, os.environ.get("HER_NAME", "there")))
        self.datetime.set_text(f"{core.date_text(now)}   {core.clock_text(now)}")
        self.clock.set_text(core.clock_text(now))
        if self.app is not None and self.app.poll() is not None:
            self.go_home()
        return True

    def _click_ok(self):
        return self.debounce.accept(GLib.get_monotonic_time() // 1000)

    def _on_tile(self, _button, tile):
        if not self._click_ok():
            return
        if tile.command[0] == "internal:help":
            self.show_help()
        elif tile.command[0] == "internal:downloads":
            self.show_downloads()
        else:
            self.launch(tile.command)

    def launch(self, command):
        self._stop_app()
        self.app = subprocess.Popen(command)
        self.main.hide()

    def _stop_app(self):
        if self.app is not None and self.app.poll() is None:
            self.app.send_signal(signal.SIGTERM)
        self.app = None

    def go_home(self):
        self._stop_app()
        self.stack.set_visible_child_name("home")
        self.main.show()

    def show_help(self):
        self._stop_app()
        page = self._page()
        for line in core.help_lines(core.support_connected()):
            label = Gtk.Label(label=line)
            label.set_line_wrap(True)
            page.pack_start(label, False, False, 0)
        self._replace_page("help", page)

    def show_downloads(self):
        page = self._page()
        files = sorted(p for p in DOWNLOADS.glob("*") if p.is_file()) if DOWNLOADS.is_dir() else []
        if not files:
            page.pack_start(Gtk.Label(label=text("downloads_empty")), False, False, 0)
        for path in files:
            button = big_button(path.name, "tile")
            url = "file://" + urllib.parse.quote(str(path))
            button.connect("clicked", lambda _b, u=url: self.launch(
                ["firefox-esr", "--no-remote", "--kiosk", "-P", "google", u]))
            page.pack_start(button, False, False, 0)
        self._replace_page("downloads", page)

    def _replace_page(self, name, page):
        old = self.stack.get_child_by_name(name)
        if old is not None:
            self.stack.remove(old)
        page.show_all()
        self.stack.add_named(page, name)
        self.stack.set_visible_child_name(name)
        self.main.show()

    def back(self):
        subprocess.Popen(["wtype", "-M", "alt", "-k", "Left", "-m", "alt"])

    def print_page(self):
        subprocess.Popen(["wtype", "-M", "ctrl", "-k", "p", "-m", "ctrl"])
        GLib.timeout_add_seconds(2, lambda: Toast(text("print_sent")) and False)

    def volume(self, step):
        subprocess.Popen(["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", step])

    # ---- messages ----
    def _poll_spool(self):
        for message in messages.read_new_messages(messages.SPOOL, self.seen_messages):
            Toast(message)
        return True

    def _poll_status(self):
        current = {m for m in (messages.connectivity_message(), messages.printer_message(),
                               messages.usb_blocked_message()) if m}
        for message in current - self.active_alerts:   # only announce a problem when it first appears
            Toast(message)
        self.active_alerts = current
        return True


def main():
    css = Gtk.CssProvider()
    css.load_from_path(str(HERE / "theme.css"))
    Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), css,
                                             Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    Shell()
    Gtk.main()


if __name__ == "__main__":
    main()
