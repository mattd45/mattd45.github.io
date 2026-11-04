"""Off-device tests for the download airlock (spec 6.6)."""
import importlib
import os
import shutil
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xff\xd9"
# EICAR marker split so this repo is never flagged by scanners.
EICAR = "X5O!P%@AP[4\\PZX54(P^)7CC)7}$" + "EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


def al():
    path = ROOT / "airlock" / "airlock.py"
    assert path.exists(), "airlock/airlock.py is missing"
    sys.path.insert(0, str(ROOT / "airlock"))
    return importlib.import_module("airlock")


@pytest.fixture
def dirs(tmp_path):
    q, d = tmp_path / "quarantine", tmp_path / "Downloads"
    q.mkdir(); d.mkdir()
    return q, d


class Notes:
    def __init__(self):
        self.calls = []

    def __call__(self, audience, message):
        self.calls.append((audience, message))

    def audiences(self):
        return [a for a, _ in self.calls]


def fake_scan(verdict_for_eicar="INFECTED"):
    a = al()

    def scan(path):
        data = path.read_bytes()
        return getattr(a.Verdict, verdict_for_eicar) if b"EICAR-STANDARD" in data else a.Verdict.CLEAN
    return scan


def put(q, name, data):
    f = q / name
    f.write_bytes(data if isinstance(data, bytes) else data.encode())
    return f


# ---- classify (by content, never by extension) ----
def test_classify_recognises_allowed_types(tmp_path):
    a = al()
    for name, data, kind in [("a.pdf", PDF, "pdf"), ("b.jpg", JPG, "jpg"), ("c.txt", b"hello\n", "txt")]:
        f = tmp_path / name
        f.write_bytes(data)
        assert a.classify(f) == kind, name


def test_classify_rejects_executable_renamed_as_pdf(tmp_path):
    f = tmp_path / "invoice.pdf"
    shutil.copy("/bin/ls", f)
    assert al().classify(f) is None


# ---- process ----
def test_clean_pdf_is_delivered_and_user_told(dirs):
    a = al(); q, d = dirs; n = Notes()
    f = put(q, "letter.pdf", PDF)
    assert a.process(f, d, n, scan_fn=fake_scan(), settle=0) == a.Verdict.CLEAN
    assert (d / "letter.pdf").read_bytes() == PDF and not f.exists()
    assert n.audiences() == ["user"]


def test_delivered_file_is_not_executable(dirs):
    a = al(); q, d = dirs
    a.process(put(q, "letter.pdf", PDF), d, Notes(), scan_fn=fake_scan(), settle=0)
    assert not (stat.S_IMODE((d / "letter.pdf").stat().st_mode) & 0o111)


def test_unicode_and_spaces_in_name_survive(dirs):
    a = al(); q, d = dirs
    a.process(put(q, "Résumé final.pdf", PDF), d, Notes(), scan_fn=fake_scan(), settle=0)
    assert (d / "Résumé final.pdf").exists()


def test_name_collision_keeps_both_files(dirs):
    a = al(); q, d = dirs
    (d / "a.pdf").write_bytes(b"old")
    a.process(put(q, "a.pdf", PDF), d, Notes(), scan_fn=fake_scan(), settle=0)
    assert (d / "a.pdf").read_bytes() == b"old" and (d / "a (1).pdf").read_bytes() == PDF


def test_partial_and_empty_files_are_left_alone(dirs):
    a = al(); q, d = dirs; n = Notes()
    part = put(q, "x.pdf.part", b"half")
    empty = put(q, "empty.pdf", b"")
    assert a.process(part, d, n, scan_fn=fake_scan(), settle=0) == a.Verdict.INCOMPLETE
    assert a.process(empty, d, n, scan_fn=fake_scan(), settle=0) == a.Verdict.INCOMPLETE
    assert part.exists() and empty.exists() and n.calls == [] and not list(d.iterdir())


def test_file_still_growing_is_treated_as_incomplete(dirs):
    a = al(); q, d = dirs
    f = put(q, "big.pdf", PDF)
    grow = lambda _s: f.write_bytes(f.read_bytes() + b"more")
    assert a.process(f, d, Notes(), scan_fn=fake_scan(), settle=0.01, sleep=grow) == a.Verdict.INCOMPLETE
    assert f.exists() and not list(d.iterdir())


def test_infected_file_is_deleted_and_admin_alerted(dirs):
    a = al(); q, d = dirs; n = Notes()
    f = put(q, "notes.txt", EICAR)
    assert a.process(f, d, n, scan_fn=fake_scan(), settle=0) == a.Verdict.INFECTED
    assert not f.exists() and not list(d.iterdir())
    assert set(n.audiences()) == {"user", "admin"}


def test_disallowed_type_is_deleted_without_scanning(dirs):
    a = al(); q, d = dirs; n = Notes()
    f = q / "invoice.pdf"
    shutil.copy("/bin/ls", f)
    def boom(_p): raise AssertionError("scan must not run for a blocked type")
    assert a.process(f, d, n, scan_fn=boom, settle=0) == a.Verdict.BLOCKED_TYPE
    assert not f.exists() and set(n.audiences()) == {"user", "admin"}


def test_scanner_down_holds_file_and_asks_for_help(dirs):
    a = al(); q, d = dirs; n = Notes()
    f = put(q, "letter.pdf", PDF)
    down = lambda _p: a.Verdict.SCAN_ERROR
    assert a.process(f, d, n, scan_fn=down, settle=0) == a.Verdict.SCAN_ERROR
    assert f.exists() and not list(d.iterdir())
    assert set(n.audiences()) == {"user", "admin"}


# ---- scan (real exit-code mapping, with a fake clamdscan) ----
def fake_clamdscan(tmp_path, code):
    script = tmp_path / f"clamdscan{code}"
    script.write_text(f"#!/bin/sh\nexit {code}\n")
    script.chmod(0o755)
    return str(script)


@pytest.mark.parametrize("code,name", [(0, "CLEAN"), (1, "INFECTED"), (2, "SCAN_ERROR")])
def test_scan_maps_clamdscan_exit_codes(tmp_path, code, name):
    a = al()
    f = tmp_path / "f.txt"; f.write_text("x")
    assert a.scan(f, clamdscan=fake_clamdscan(tmp_path, code)) == getattr(a.Verdict, name)


def test_scan_with_missing_scanner_is_scan_error(tmp_path):
    a = al()
    f = tmp_path / "f.txt"; f.write_text("x")
    assert a.scan(f, clamdscan=str(tmp_path / "nope")) == a.Verdict.SCAN_ERROR


# ---- admin alert and the --once entry point ----
def test_admin_alert_calls_helper_when_present_and_survives_when_missing(tmp_path, monkeypatch):
    a = al()
    out = tmp_path / "out.txt"
    helper = tmp_path / "alert"
    helper.write_text(f'#!/bin/sh\necho "$1" > {out}\n'); helper.chmod(0o755)
    monkeypatch.setenv("SENIOR_ALERT", str(helper))
    a.alert_admin("scanner down")
    assert out.read_text().strip() == "scanner down"
    monkeypatch.setenv("SENIOR_ALERT", str(tmp_path / "absent"))
    a.alert_admin("still fine")  # must not raise


def test_once_mode_delivers_clean_files_end_to_end(dirs, tmp_path, monkeypatch):
    a = al(); q, d = dirs
    put(q, "letter.pdf", PDF)
    monkeypatch.setenv("AIRLOCK_CLAMDSCAN", fake_clamdscan(tmp_path, 0))
    monkeypatch.setenv("SENIOR_ALERT", str(tmp_path / "absent"))
    monkeypatch.setattr(a, "notify_user", lambda msg: None)
    assert a.main(["--once", str(q), str(d)]) == 0
    assert (d / "letter.pdf").exists()


# ---- safety: scanned bytes are the delivered bytes ----
def test_delivered_bytes_are_the_bytes_that_were_scanned(dirs):
    a = al(); q, d = dirs
    f = put(q, "l.pdf", PDF)
    seen = {}

    def scan(p):
        seen["path"], seen["data"] = p, p.read_bytes()
        f.write_bytes(b"SWAPPED AFTER SCAN")   # attacker rewrites the original mid-scan
        return a.Verdict.CLEAN

    a.process(f, d, Notes(), scan_fn=scan, settle=0)
    assert seen["path"] != f                      # scanned a private copy
    assert (d / "l.pdf").read_bytes() == seen["data"] == PDF


# ---- held files: quiet retries, delivered once the scanner is back ----
def test_sweep_holds_quietly_then_delivers_when_scanner_recovers(dirs):
    a = al(); q, d = dirs; n = Notes(); state = a.SweepState()
    f = put(q, "l.pdf", PDF)
    clock, up = [0.0], [False]
    scan = lambda p: a.Verdict.CLEAN if up[0] else a.Verdict.SCAN_ERROR
    run = lambda: a.sweep(q, d, n, scan_fn=scan, settle=0, now=lambda: clock[0], state=state)

    run()
    assert len(n.calls) == 2 and f.exists()          # user + admin told once
    clock[0] = 100; run()
    assert len(n.calls) == 2                          # inside retry window: untouched
    clock[0] = 400; run()
    assert len(n.calls) == 2 and f.exists()          # retried, still down, no repeat notices
    up[0], clock[0] = True, 800; run()
    assert (d / "l.pdf").exists() and n.calls[-1][0] == "user"


# ---- hand-off to the shell ----
def test_notify_user_writes_a_message_file_for_the_shell(tmp_path, monkeypatch):
    a = al()
    spool = tmp_path / "messages"
    monkeypatch.setenv("SENIOR_MESSAGES", str(spool))
    a.notify_user("Checked and safe.")
    files = list(spool.iterdir())
    assert len(files) == 1 and files[0].read_text() == "Checked and safe."
    assert stat.S_IMODE(files[0].stat().st_mode) & 0o004      # readable by her session
