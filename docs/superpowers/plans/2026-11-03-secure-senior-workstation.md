# Secure Senior Workstation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision one Raspberry Pi 5 into a locked-down appliance for an elderly user (Email, Facebook, Writer, Documents, Print, Help) that the administrator can support remotely.

**Architecture:** A scripted provisioning kit (numbered idempotent bash scripts + config templates) plus two small custom programs: the download "airlock" (Python) and the Home screen (Python/GTK). Each requirement is pinned by a check script under `verify/checks/` that fails on an unprovisioned Pi and passes after the matching provisioning script runs. Pure-Python logic is unit-tested with pytest on any machine; system checks run on the Pi.

**Tech Stack:** Raspberry Pi OS Desktop 64-bit (compositor and Debian release to be confirmed in Task 1), bash + shellcheck, Python 3 + pytest + PyGObject (GTK 3), Firefox ESR with `policies.json`, uBlock Origin, ClamAV (`clamd`), ufw, CUPS + `ipp-usb`, rclone (crypt), systemd, Raspberry Pi Connect.

**Spec:** `docs/superpowers/specs/2026-11-03-secure-senior-workstation-design.md`

**Repo location:** developed in `senior-pi/` on this branch. This repo is public; the kit documents the device's security posture, so move `senior-pi/` to a **private** repo before merging. Secrets (`config.env`, rclone config, health-check URL) are never committed.

## Global Constraints

- Hardware: Raspberry Pi 5, 4GB RAM; boot from USB SSD (or high-endurance 64GB MicroSD); existing monitor/keyboard/mouse; **mouse-only UX** (no touch, drag-drop, double-click or right-click needed).
- Accounts: standard non-sudo user `grandma` (auto-login, linger enabled); separate `admin` account; root login disabled.
- Disabled: SSH, VNC, Bluetooth (if unused), USB storage auto-mount (USB printer class stays allowed), browser DNS-over-HTTPS.
- Firewall: `ufw` default deny incoming; outgoing restricted to web 80/443, DNS, NTP, and what Pi Connect, rclone and the health-check need. Filtering DNS (Quad9).
- Browser: Firefox ESR, root-owned `policies.json`; domain allow-list; uBlock Origin force-installed and locked; fullscreen, devtools, private browsing, `about:config`, add-on installs, notifications, `file://`, password export and pop-ups disabled; default zoom 130%; no address bar or tab strip.
- LibreOffice macros disabled. Download dirs mounted `noexec`.
- Downloads: quarantine -> ClamAV scan + file-type check -> `~grandma/Documents/Downloads`. Allowed types: PDF, DOC/DOCX/ODT, JPG/PNG, TXT; all others deleted and admin alerted.
- Backup: nightly rclone crypt sync of Documents to a dedicated Google Drive folder. Updates: unattended security upgrades, nightly reboot window, health-check ping.
- UI: Home tiles = Email, Facebook, Write a Letter, My Documents, Help. Bottom bar = Home, Print, Volume, Help. Block page text: "That page isn't available. Tap Help and {ADMIN_NAME} will sort it out." Placeholders `{ADMIN_NAME}`, `{ADMIN_PHONE}` come from `config.env`.
- Every script is idempotent (safe to re-run) and passes `shellcheck`.

## Review Focus

1. **Partial or odd downloads:** Firefox `.part` files, spaces/unicode in filenames, zero-byte files must not be scanned mid-write, crash the watcher, or be delivered. (Task 5)
2. **Extension spoofing:** a `.pdf` that is really an executable/script must be blocked by MIME type, not extension. (Task 5)
3. **Scanner unavailable:** if `clamd` is down or signatures are stale, files stay quarantined and she is told to ask for help; nothing is delivered unscanned. (Task 5)
4. **Allow-list breakage:** Gmail/Facebook sign-in and redirects use extra Google/Facebook domains; a too-tight list yields an endless block page. (Task 4)
5. **Offline / printer fault:** Wi-Fi down or printer out of paper/ink shows a plain-language message on Home, not a blank page or raw error. (Tasks 6, 8)

## File Structure

```
senior-pi/
  config.env.example          # ADMIN_NAME, ADMIN_PHONE, PRINTER_URI, HEALTHCHECK_URL, GDRIVE_REMOTE
  provision.sh                # runs scripts/NN-*.sh in order
  scripts/01-base.sh 02-network.sh 03-remote.sh 04-browser.sh 05-airlock.sh
          06-desktop.sh 07-printing.sh 08-backup.sh 09-monitoring.sh
  browser/policies.json.tmpl  allowlist.txt  blocked.html.tmpl
  airlock/airlock.py          airlock.service
  home/home.py  tiles.json    home.desktop
  verify/run.sh  verify/checks/NN-*.sh   # acceptance checks (spec section 9)
  tests/test_airlock.py  tests/test_home.py  tests/test_policies.py
  docs/runbook.md             # rebuild, golden image, admin escalation
```

---

### Task 1: Scaffold, test harness and platform discovery

**Files:**
- Create: `senior-pi/config.env.example`, `senior-pi/provision.sh`, `senior-pi/verify/run.sh`, `senior-pi/docs/runbook.md`, `.github/workflows/senior-pi.yml`

**Interfaces:**
- Produces: `provision.sh [--only NN]` sources `config.env` and runs `scripts/NN-*.sh`; `verify/run.sh [--only NN]` runs `verify/checks/NN-*.sh`, prints `PASS|FAIL <name>`, exits non-zero if any FAIL.

- [ ] **Step 1: Write `verify/run.sh` and a self-test**: with no checks present it exits 0; with a check that `exit 1` it prints `FAIL` and exits 1 (pytest/bats-free shell test in `tests/run_selftest.sh`).
- [ ] **Step 2: Run the self-test; expected FAIL** (`run.sh` missing).
- [ ] **Step 3: Implement `run.sh`, `provision.sh`, `config.env.example`** (keys listed above; `.gitignore` excludes `config.env`).
- [ ] **Step 4: Run the self-test; expected PASS.** Add a CI workflow running `shellcheck` on `senior-pi/**/*.sh` and `pytest senior-pi/tests`.
- [ ] **Step 5: On the Pi, record in `docs/runbook.md`:** `cat /etc/os-release`, Pi OS version, compositor (`echo $XDG_CURRENT_DESKTOP`), Firefox ESR availability (`apt policy firefox-esr`), `python3 -c "import gi"`. Later tasks use these values.
- [ ] **Step 6: Commit** `chore: scaffold senior-pi provisioning kit`.

### Task 2: Base OS, accounts, updates

**Files:** Create `scripts/01-base.sh`, `verify/checks/01-base.sh`

**Interfaces:** Consumes `config.env`. Produces users `grandma` (uid 1000, no sudo, autologin, linger) and `admin` (sudo), unattended-upgrades enabled, nightly reboot at 04:00 via systemd timer `nightly-reboot.timer`.

- [ ] **Step 1: Write `01-base.sh` check** asserting: `id grandma` exists and is not in groups `sudo`/`adm`; SSH inactive and disabled; root login locked (`passwd -S root` shows `L`); `systemctl is-enabled unattended-upgrades` and `nightly-reboot.timer`; Bluetooth service disabled.
- [ ] **Step 2: Run `verify/run.sh --only 01` on the fresh Pi; expected FAIL.**
- [ ] **Step 3: Implement `01-base.sh`** (idempotent `useradd`/`systemctl disable` guarded by existence checks; autologin via the display-manager config from Task 1 discovery; `loginctl enable-linger grandma`; `unattended-upgrades` including Raspberry Pi repo origins).
- [ ] **Step 4: Re-run the check; expected all PASS.** Reboot; confirm auto-login lands on the desktop.
- [ ] **Step 5: Commit** `feat: base OS accounts and updates`.

### Task 3: Firewall, filtering DNS and remote access

**Files:** Create `scripts/02-network.sh`, `scripts/03-remote.sh`, `verify/checks/02-network.sh`, `verify/checks/03-remote.sh`

**Interfaces:** Produces `ufw` policy per Global Constraints, system DNS = Quad9 (`9.9.9.9`) via NetworkManager/`systemd-resolved`, Pi Connect enabled for `admin` (shell) and `grandma` (screen share) — escalation approach is verified in step 1 below.

- [ ] **Step 1 (spike, on the Pi):** confirm Pi Connect screen-share for `grandma` and shell for `admin` can both be linked to the admin's Raspberry Pi ID. If not possible, document and switch to key-only Tailscale SSH for admin access. Record the decision in `docs/runbook.md`.
- [ ] **Step 2: Write checks:** `ufw status verbose` contains `Default: deny (incoming)`; `ss -tlnp` shows no non-loopback listeners; `resolvectl status` shows `9.9.9.9`; `rpi-connect status` is signed in; `curl -s https://dns.quad9.net/` (or Quad9 test) shows filtering active.
- [ ] **Step 3: Run; expected FAIL.**
- [ ] **Step 4: Implement the two scripts.** Outgoing rules: allow 80/443, 53, 123, plus ports/hosts discovered for Pi Connect, rclone and the health-check; default deny outgoing last. Pi Connect link step is interactive and documented in the runbook.
- [ ] **Step 5: Re-run checks; expected PASS.** Reboot and confirm remote shell and screen sharing still work.
- [ ] **Step 6: Commit** `feat: firewall, filtering DNS, remote access`.

### Task 4: Browser policies and allow-list

**Files:** Create `browser/policies.json.tmpl`, `browser/allowlist.txt`, `browser/blocked.html.tmpl`, `scripts/04-browser.sh`, `tests/test_policies.py`, `verify/checks/04-browser.sh`

**Interfaces:** Produces `/etc/firefox/policies/policies.json` (root-owned 0644) and `/usr/local/share/senior-pi/blocked.html`; `allowlist.txt` is one domain per line.

- [ ] **Step 1: Write `tests/test_policies.py`:** renders the template with a sample config; asserts valid JSON; `policies["WebsiteFilter"]["Block"] == ["<all_urls>"]` and `Exceptions` contains every domain in `allowlist.txt`; `ExtensionSettings` force-installs `uBlock0@raymondhill.net` with `installation_mode == "force_installed"`; `DisableDeveloperTools`, `DisablePrivateBrowsing`, `BlockAboutConfig`, `DisableFormHistory` true; `Preferences` sets `layout.css.devPixelsPerPx` to `1.3`, `full-screen-api.enabled` false, `network.trr.mode` 5 (DoH off).
- [ ] **Step 2: Run `pytest tests/test_policies.py`; expected FAIL** (template missing).
- [ ] **Step 3: Implement the template and `render_policies(allowlist: list[str], admin_name: str) -> dict` in `scripts/render_policies.py`.** Seed `allowlist.txt` with Google sign-in/Gmail domains (`mail.google.com`, `accounts.google.com`, `*.gstatic.com`, `*.googleusercontent.com`) and Facebook (`facebook.com`, `*.fbcdn.net`); the block page uses `{ADMIN_NAME}` and `{ADMIN_PHONE}` text from Global Constraints.
- [ ] **Step 4: Run the tests; expected PASS.**
- [ ] **Step 5: On the Pi, write `verify/checks/04-browser.sh`** (policy file root-owned, not writable by grandma; `grandma` cannot `sudo`) and `04-browser.sh` install script; then **log in to Gmail and Facebook as grandma** and add every domain that produces a block page to `allowlist.txt` (record each in the commit message). Confirm `https://example.com` shows the block page.
- [ ] **Step 6: Commit** `feat: Firefox policies, allow-list and block page`.

### Task 5: Download airlock

**Files:** Create `airlock/airlock.py`, `airlock/airlock.service`, `scripts/05-airlock.sh`, `tests/test_airlock.py`, `verify/checks/05-airlock.sh`

**Interfaces:**
- Produces:
  - `class Verdict(Enum): CLEAN, INFECTED, BLOCKED_TYPE, SCAN_ERROR, INCOMPLETE`
  - `def classify(path: Path) -> str | None`: returns one of `pdf, doc, docx, odt, jpg, png, txt` from `file --mime-type` (never the extension), else `None`.
  - `def scan(path: Path) -> Verdict`: `clamdscan --fdpass`; returns `SCAN_ERROR` if `clamd` is unreachable.
  - `def process(path: Path, downloads_dir: Path, notify: Callable[[str, str], None]) -> Verdict`.
- Firefox download dir = `/var/lib/senior-pi/quarantine` (owned `airlock`, not readable by grandma). Watcher is a systemd service using `inotify` (`inotifywait`) on `close_write`/`moved_to`.

- [ ] **Step 1: Write failing tests** (scan stubbed with a fake `clamdscan` function in tests): `classify` returns `"pdf"` for real PDF bytes and `None` for an ELF binary renamed `x.pdf` (Review Focus 2); `process` ignores `*.part` and zero-byte files and returns `INCOMPLETE` (Review Focus 1); a file named `Résumé final.pdf` is delivered intact; a clean PDF is moved to `downloads_dir` and `notify("Checked and safe", ...)` called; EICAR (built from two split string literals) returns `INFECTED`, is deleted and the admin alert called; with the scan stub raising `ConnectionError`, `process` returns `SCAN_ERROR`, leaves the file in quarantine and calls `notify` with the ask-for-help message (Review Focus 3).
- [ ] **Step 2: Run `pytest tests/test_airlock.py`; expected FAIL.**
- [ ] **Step 3: Implement the module** exactly to the interfaces; delivery is an atomic `os.replace` after a size-stable check; deletion on `INFECTED`/`BLOCKED_TYPE`; `notify` default uses `notify-send` for her and an email/ping to the admin via the Task 9 alert helper.
- [ ] **Step 4: Run the tests; expected PASS.**
- [ ] **Step 5: On the Pi, write the check and installer:** install `clamav-daemon`, `freshclam` running, `airlock.service` enabled, quarantine mount options `noexec,nosuid,nodev`; check downloads real EICAR via Firefox (test page on the allow-list is temporarily added) and verifies it never reaches `Documents/Downloads`, while a clean PDF does. Also stop `clamav-daemon` and confirm a PDF stays quarantined with the help message.
- [ ] **Step 6: Memory check:** with Firefox, LibreOffice and `clamd` open, `free -m` shows >= 500MB available; if not, enable zram/SSD swap in `05-airlock.sh` and re-measure.
- [ ] **Step 7: Commit** `feat: download airlock with ClamAV scanning`.

### Task 6: Home screen

**Files:** Create `home/home.py`, `home/tiles.json`, `home/home.desktop`, `tests/test_home.py`, `verify/checks/06-home.sh`

**Interfaces:**
- `def load_tiles(path: Path) -> list[Tile]` where `Tile = {label: str, command: list[str], icon: str}`; order: Email, Facebook, Write a Letter, My Documents, Help.
- `def connectivity_message() -> str | None`: `None` when online, else "The internet isn't connected. Tap Help and {ADMIN_NAME} will sort it out." (Review Focus 5).
- `def printer_message() -> str | None`: maps CUPS printer state/reasons (`media-empty`, `marker-supply-low`, `offline`) to "The printer needs paper or ink. Ask {ADMIN_NAME}." etc.
- Bottom bar buttons: Home, Print, Volume, Help; Help window shows `{ADMIN_NAME}`, `{ADMIN_PHONE}` and remote-support status (Pi Connect signed in).

- [ ] **Step 1: Write `tests/test_home.py`:** `load_tiles` returns exactly the five labels in order; every tile `command` is a non-empty list; `connectivity_message()` returns the text above when the connectivity probe is stubbed offline, else `None`; `printer_message` returns the paper/ink text for `media-empty`.
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement `home.py` (GTK 3, fullscreen, no window decorations).** Style: large (>= 28pt) text, high contrast, big click targets, single-click only. Launch commands: Gmail/Facebook open a dedicated Firefox kiosk window on their URL (separate profile each); Writer via `libreoffice --writer`; Documents opens a restricted file window or LibreOffice open dialog rooted at Documents. Apps open maximized; the bottom bar stays visible.
- [ ] **Step 4: Run the unit tests; expected PASS.** Then smoke test headless: `xvfb-run python3 home/home.py --selftest` exits 0.
- [ ] **Step 5: On the Pi**, autostart via `home.desktop`; the check verifies the process runs after login; manually click every tile and the bar, using only the mouse.
- [ ] **Step 6: Commit** `feat: Home screen`.

### Task 7: Desktop and OS lockdown

**Files:** Create `scripts/06-desktop.sh`, `verify/checks/07-desktop.sh`

**Interfaces:** Produces: panel/menu stripped to launcher only; no terminal; no console switching; root-owned read-only desktop configs for `grandma`; udev rule blocking USB mass storage but allowing printers; LibreOffice macro security set to the disabled level via an admin-owned registry config.

- [ ] **Step 1: Write the check:** `which lxterminal x-terminal-emulator` absent for grandma; `grandma` cannot write the panel/compositor config (`test ! -w`); `Ctrl+Alt+F2` and terminal keybindings absent from the compositor config; udev rule present; LibreOffice config has macro security at the highest level; plugging a USB stick (manual step, recorded) does not mount while the printer enumerates.
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement `06-desktop.sh`** (remove packages rather than hiding icons; `chown root` + `chmod a-w` configs; udev rule on `bInterfaceClass` 08 vs 07).
- [ ] **Step 4: Re-run the check; expected PASS.** Reboot and try: terminal shortcuts, right-click panel, Settings access — all unavailable.
- [ ] **Step 5: Commit** `feat: desktop and OS lockdown`.

### Task 8: Printing

**Files:** Create `scripts/07-printing.sh`, `verify/checks/08-printing.sh`

**Interfaces:** Consumes `PRINTER_URI` (from `config.env`) and printer make/model (**open item:** unknown). Produces a default CUPS printer named `Home-Printer`, not manageable by grandma.

- [ ] **Step 1: Identify the printer:** read make/model from the label; run `lsusb`, `ipptool -tv ipp://localhost:60000/ipp/print get-printer-attributes.test` (driverless via `ipp-usb`) and `lpinfo -v`. Choose per spec order: driverless, then open-source driver (`hplip`, `epson-inkjet-printer-escpr`, `gutenprint`), then proprietary (ARM-compatible), else replace with a driverless IPP Wi-Fi printer. Record the result in the runbook.
- [ ] **Step 2: Write the check:** `lpstat -d` shows `Home-Printer`; `lp` of a test page returns a job id and the job completes (`lpstat -W completed`); `grandma` cannot run `lpadmin`.
- [ ] **Step 3: Run; expected FAIL.**
- [ ] **Step 4: Implement `07-printing.sh`** for the chosen driver; set `lpadmin` to root/admin only; wire the Home bar's Print button to open the print dialog.
- [ ] **Step 5: Re-run; expected PASS.** Test with the paper tray empty and confirm Task 6's `printer_message()` text appears on Home.
- [ ] **Step 6: Commit** `feat: USB printing`.

### Task 9: Backup, monitoring and alerts

**Files:** Create `scripts/08-backup.sh`, `scripts/09-monitoring.sh`, `verify/checks/09-backup.sh`

**Interfaces:** Produces `senior-pi-backup.timer` (daily 02:00) running `rclone sync ~grandma/Documents gdrive-crypt:` ; `senior-pi-heartbeat.timer` (every 5 minutes) pinging `HEALTHCHECK_URL`; `/usr/local/bin/senior-pi-alert "<message>"` used by Task 5.

- [ ] **Step 1: Write the check:** both timers active; `rclone lsd gdrive-crypt:` succeeds; a marker file written to Documents appears in Drive within one manual backup run; the heartbeat URL returns 200.
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement.** rclone's Google Drive OAuth is interactive: document the headless `rclone authorize "drive"` flow (done on the admin's laptop) in the runbook; `rclone crypt` over a dedicated Drive folder; config stored root-readable only, never committed. Backup failure calls `senior-pi-alert`.
- [ ] **Step 4: Re-run; expected PASS.** Also test: disconnect Wi-Fi, run backup, confirm alert fires; reconnect, confirm next run succeeds. Restore test: delete a Documents file, pull it back from Drive.
- [ ] **Step 5: Commit** `feat: Drive backup and monitoring`.

### Task 10: Acceptance suite, golden image and usability session

**Files:** Modify `verify/run.sh` docs; Create `verify/checks/99-acceptance.sh`, extend `docs/runbook.md`

- [ ] **Step 1: Encode spec section 9** as checks not already covered (non-allow-listed site blocked; fullscreen fake-alert page blocked; macro document does not run macros; USB stick not mounted). Manual items are listed in `docs/runbook.md` with a pass/fail table.
- [ ] **Step 2: Run `provision.sh` on a fresh card, then `verify/run.sh`; expected all PASS.**
- [ ] **Step 3: Reboot test:** confirm Home loads, Pi Connect reconnects, airlock and backup timers are active.
- [ ] **Step 4: Rebuild test:** re-flash a spare device from the runbook and time it (target under one hour); create the golden image and store it off the Pi.
- [ ] **Step 5: 30-minute usability session with her** (mouse only): she opens email, writes and prints a letter, and finds Help. Record friction in the runbook; adjust tile labels, sizes and wording; re-run `verify/run.sh`.
- [ ] **Step 6: Place the printed "No one from Microsoft, Apple or your bank will ever call..." card by the monitor.**
- [ ] **Step 7: Commit** `docs: runbook and acceptance results`.

---

## Self-review notes
- Spec coverage: sections 6.1->Task 4, 6.2->Tasks 2/7, 6.3/6.4->Task 3, 6.5->Task 5, 6.6->Task 8, 6.7/6.8->Tasks 9/10, UX->Task 6, acceptance->Task 10.
- Open items from the spec remain explicit: printer model (Task 8 step 1), Pi Connect escalation (Task 3 step 1), allow-list contents (Task 4 step 5), outbound firewall list (Task 3 step 4), ADMIN_NAME/ADMIN_PHONE (config).
- Pure logic (`classify`, `process`, `load_tiles`, policy rendering) is unit-tested off-device; hardware-dependent steps are verified on the Pi.
