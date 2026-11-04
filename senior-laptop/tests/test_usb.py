"""Off-device tests for the USBGuard helpers (spec 6.3; Review Focus 5)."""
import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MOUSE = 'allow id 046d:c077 serial "" name "USB Optical Mouse" hash "aaa" parent-hash "bbb" via-port "1-2" with-interface 03:01:02 with-connect-type "hotplug"'
KEYBOARD = 'allow id 046d:c31c serial "" name "Keyboard" hash "ccc" parent-hash "bbb" via-port "1-3" with-interface { 03:01:01 03:00:00 } with-connect-type "hotplug"'
PRINTER = 'allow id 03f0:1d17 serial "X1" name "DeskJet" hash "ddd" parent-hash "bbb" via-port "1-4" with-interface { 07:01:02 07:01:02 } with-connect-type "hotplug"'
HUB = 'allow id 1d6b:0002 serial "0000" name "xHCI Host Controller" hash "eee" parent-hash "fff" via-port "usb1" with-interface 09:00:00 with-connect-type "not used"'
WEBCAM = 'allow id 0c45:6a10 serial "" name "Integrated Camera" hash "ggg" parent-hash "hhh" via-port "1-5" with-interface { 0e:01:00 0e:02:00 } with-connect-type "not used"'
STICK = 'allow id 0951:1666 serial "S" name "DataTraveler" hash "iii" parent-hash "bbb" via-port "1-6" with-interface 08:06:50 with-connect-type "hotplug"'
BLUETOOTH = 'allow id 8087:0026 serial "" name "Bluetooth" hash "jjj" parent-hash "hhh" via-port "1-7" with-interface { e0:01:01 e0:01:01 } with-connect-type "not used"'
MIXED = 'allow id 1111:2222 serial "" name "Combo" hash "kkk" parent-hash "bbb" via-port "1-8" with-interface { 03:01:01 08:06:50 } with-connect-type "hotplug"'


def tools():
    path = ROOT / "scripts" / "usbguard_tools.py"
    assert path.exists(), "scripts/usbguard_tools.py is missing"
    sys.path.insert(0, str(ROOT / "scripts"))
    return importlib.import_module("usbguard_tools")


def test_filter_keeps_mouse_keyboard_printer_and_hubs():
    out = tools().filter_rules("\n".join([MOUSE, KEYBOARD, PRINTER, HUB]))
    assert out.splitlines() == [MOUSE, KEYBOARD, PRINTER, HUB]


def test_filter_drops_webcam_storage_bluetooth_and_mixed_devices():
    out = tools().filter_rules("\n".join([MOUSE, WEBCAM, STICK, BLUETOOTH, MIXED]))
    assert out.splitlines() == [MOUSE]


def test_filter_ignores_comments_blank_and_non_allow_lines():
    text = "# generated\n\n" + MOUSE + "\nblock id 1:2 with-interface 03:01:01\n"
    assert tools().filter_rules(text).splitlines() == [MOUSE]


def test_count_input_devices_counts_hid_rules():
    t = tools()
    assert t.count_input_devices("\n".join([MOUSE, KEYBOARD, PRINTER, HUB])) == 2
    assert t.count_input_devices(PRINTER) == 0


def feed(parser, text):
    return [parser.feed(line) for line in text.strip().splitlines()]


INSERT_BLOCKED_HID = """
[device] PresenceChanged: id=12
 event=Insert
 target=block
 device_rule=block id 046d:c52b serial "" name "New Mouse" hash "zzz" parent-hash "bbb" via-port "1-9" with-interface 03:01:02 with-connect-type "hotplug"
"""
INSERT_BLOCKED_STORAGE = INSERT_BLOCKED_HID.replace("03:01:02", "08:06:50").replace("New Mouse", "Stick")
INSERT_ALLOWED_HID = INSERT_BLOCKED_HID.replace("target=block", "target=allow")
REMOVE_HID = INSERT_BLOCKED_HID.replace("event=Insert", "event=Remove")


def test_watcher_flags_a_blocked_input_device_once_fully_parsed():
    p = tools().UsbWatchParser()
    results = feed(p, INSERT_BLOCKED_HID)
    assert results[-1] is True and not any(results[:-1])


def test_watcher_ignores_blocked_storage_allowed_devices_and_removals():
    t = tools()
    for sample in (INSERT_BLOCKED_STORAGE, INSERT_ALLOWED_HID, REMOVE_HID):
        assert not any(feed(t.UsbWatchParser(), sample)), sample


def test_watcher_state_resets_between_events():
    p = tools().UsbWatchParser()
    feed(p, INSERT_ALLOWED_HID)
    assert feed(p, INSERT_BLOCKED_HID)[-1] is True
