# Secure Senior Workstation Implementation Plan (Laptop edition)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provision one refurbished Lenovo IdeaPad 3 15ADA05 running hardened Debian into a locked-down appliance for an elderly user (Gmail, Google Docs, Facebook, Downloads, Print, Help) that the administrator can support remotely.

**Architecture:** A scripted provisioning kit (numbered idempotent bash scripts + config templates) plus two small custom programs: the download "airlock" (Python) and the Home screen (Python/GTK). Each requirement is pinned by a check script under `verify/checks/` that fails on an unprovisioned machine and passes after the matching script runs. Pure-Python logic is unit-tested with pytest anywhere; system checks run on the laptop.

**Tech Stack:** Debian stable (version recorded in Task 1), bash + shellcheck, Python 3 + pytest + PyGObject (GTK 3), Firefox ESR with `policies.json`, uBlock Origin, AppArmor, USBGuard, btrfs + snapper, LUKS2 + TPM2, ClamAV, ufw, CUPS + `ipp-usb`, Tailscale, RustDesk, systemd, lynis, OpenSCAP.

**Spec:** `docs/superpowers/specs/2026-11-03-secure-senior-workstation-design.md`

**Repo location:** developed in `senior-laptop/` on this branch. This repo is public and the kit documents the device's security posture, so move `senior-laptop/` to a **private** repo before merging. Secrets (`config.env`, Tailscale auth keys, health-check URL) are never committed.

## Global Constraints

- Hardware: Lenovo IdeaPad 3 15ADA05 (81W1), Ryzen 3, 128GB SSD, RAM upgraded to 8GB if the spare slot is confirmed (else 4GB with zram); Lenovo Conservation Mode on; mouse and keyboard UX (no gestures, drag-drop or right-click needed).
- OS: Debian stable, minimal desktop, Windows wiped. **No office suite installed**; writing is Google Docs.
- Accounts: standard non-sudo `grandma` (auto-login); separate `admin`; root login disabled.
- Firmware: BIOS supervisor password, Secure Boot on, boot order locked after install. Disk: LUKS2 on btrfs with TPM2 auto-unlock, else unencrypted + BIOS lock (decision recorded in runbook).
- Disabled: SSH server, VNC, Bluetooth (if unused), USB storage. USBGuard default-block, allow only her mouse, keyboard and printer by device ID.
- Firewall: `ufw` default deny incoming; outgoing = web 80/443, DNS, NTP, plus what Tailscale, RustDesk and the health-check need. Filtering DNS = Quad9 (`9.9.9.9`); browser DoH off.
- Browser: Firefox ESR, root-owned `policies.json`; domain allow-list; uBlock Origin force-installed and locked; fullscreen, devtools, private browsing, `about:config`, add-ons, notifications, `file://`, password export, pop-ups disabled; zoom 130%; no address bar or tab strip; two profiles (Google, Facebook); AppArmor-confined to its profile and Downloads.
- Mounts: `noexec,nosuid,nodev` on `/tmp`, `/home` and download dirs. Boot clears browser cache and temp files; logins and Downloads persist.
- Downloads: quarantine -> ClamAV scan + MIME check -> `~grandma/Downloads`. Allowed: PDF, DOC/DOCX, JPG/PNG, TXT; everything else deleted (infected/disallowed) or held (scanner unavailable).
- Updates: unattended security upgrades with a snapper snapshot before each; nightly reboot at 04:00; health-check heartbeat every 5 minutes.
- Delivery: fully pre-configured before handover (her Wi-Fi saved, Gmail and Facebook signed in with 2-step verification, printer working, files in Drive, Tailscale joined); 48-hour bench burn-in with no alerts.
- UI: Home tiles = Email, Facebook, Write a Letter (Google Docs), My Downloads, Help. Bottom bar = Back, Home, Print, Volume, Help. Block page text: "That page isn't available. Tap Help and {ADMIN_NAME} will sort it out." Placeholders `{ADMIN_NAME}`, `{ADMIN_PHONE}` from `config.env`.
- Usability (spec 7.1): shell text >= 28px, tile labels 40px, buttons >= 72px; single-click only (double-clicks ignored for 600ms); one confirmation for turning off; no unsolicited prompts; all user-facing text in `shell/copy.py` in plain words.
- Audit targets: Lynis hardening index >= 80; `nmap` of LAN and tailnet addresses shows no open ports.
- Every script is idempotent and passes `shellcheck`.

## Review Focus

1. **Partial or odd downloads:** `.part` files, spaces/unicode names, zero-byte files must not be scanned mid-write, crash the watcher or be delivered. (Task 6)
2. **Extension spoofing:** a `.pdf` that is really an executable must be blocked by MIME type. (Task 6)
3. **Scanner unavailable:** if `clamd` is down or signatures are stale, files stay quarantined with a "ask {ADMIN_NAME}" message; nothing is delivered unscanned. (Task 6)
4. **Allow-list breakage:** Google sign-in, Docs/Drive and Facebook use many extra domains; a too-tight list gives an endless block page. (Task 5)
5. **USBGuard lock-out:** a replaced mouse/keyboard or printer is blocked and she is stranded; there must be an admin recovery path and a plain message. (Task 8)
6. **Double-click habit:** a double-click on a tile or a repeated click on a confirm button must not open two windows or auto-confirm "Turn off". (Task 7)
7. **Unexpected prompts:** a Firefox restore-session, cookie banner or update dialog that the shell cannot explain stops her. (Tasks 5, 7)
8. **Offline / printer fault:** Wi-Fi down or printer out of paper/ink shows a plain-language message on Home. (Tasks 7, 9)

## File Structure

```
senior-laptop/
  config.env.example          # ADMIN_NAME, ADMIN_PHONE, HER_NAME, WIFI_SSID, WIFI_PSK, HEALTHCHECK_URL, TAILSCALE_AUTHKEY, PRINTER_NAME
  provision.sh                # runs scripts/NN-*.sh in order
  scripts/01-base.sh 02-network.sh 03-remote.sh 04-hardening.sh 05-browser.sh
          06-airlock.sh 07-desktop.sh 08-printing-usb.sh 09-updates-monitoring.sh
  browser/policies.json.tmpl  allowlist.txt  blocked.html.tmpl  firefox.apparmor
  airlock/airlock.py          airlock.service
  shell/shell.py home.py bar.py help.py messages.py copy.py
  shell/tiles.json theme.css sway.conf shell.desktop
  docs/ux-spec.md
  hardening/sysctl.conf  modprobe-blacklist.conf  fstab-mounts.txt  usbguard-rules.tmpl
  verify/run.sh  verify/checks/NN-*.sh
  tests/test_airlock.py  tests/test_shell.py  tests/test_policies.py
  docs/runbook.md             # purchase checks, install, rollback, recovery, rebuild
```

---

### Task 1: Scaffold, harness, hardware prep and install

**Files:** Create `senior-laptop/config.env.example`, `provision.sh`, `verify/run.sh`, `docs/runbook.md`, `.github/workflows/senior-laptop.yml`

**Interfaces:** `provision.sh [--only NN]` sources `config.env` and runs `scripts/NN-*.sh`; `verify/run.sh [--only NN]` runs `verify/checks/NN-*.sh`, prints `PASS|FAIL <name>`, exits non-zero on any FAIL.

- [ ] **Step 1: Write a shell self-test** (`tests/run_selftest.sh`): `run.sh` with no checks exits 0; with a check that `exit 1` it prints `FAIL` and exits 1. Run it; expected FAIL (script missing).
- [ ] **Step 2: Implement `run.sh`, `provision.sh`, `config.env.example`** (`.gitignore` excludes `config.env`); self-test passes. CI runs `shellcheck` and `pytest senior-laptop/tests`.
- [ ] **Step 3: Purchase and inspection checklist in the runbook** (spec items): photos of the laptop with matching serial, power-on, keyboard/USB/Wi-Fi test, battery holds charge, no BIOS password or locks, confirm spare RAM slot; pay cash on collection.
- [ ] **Step 4: Firmware and install (manual, recorded in runbook):** update BIOS; set supervisor password; wipe Windows; install Debian stable minimal with LUKS2 + btrfs subvolumes `@` and `@home`; enable Secure Boot; set Conservation Mode; record `cat /etc/os-release`, kernel, Wi-Fi chip (`lspci -nnk | grep -A3 Network`) and RAM (`free -m`). If Wi-Fi needs non-free firmware, record the package.
- [ ] **Step 5: TPM unlock spike:** `systemd-cryptenroll --tpm2-device=auto`; reboot; expected: boots without a passphrase prompt. If it fails reliably, remove encryption and record the decision.
- [ ] **Step 6: Commit** `chore: scaffold senior-laptop kit and install notes`.

### Task 1b: Quick design check with her

**Files:** Create `senior-laptop/docs/ux-spec.md`

**Interfaces:** Produces the values Task 7 uses: tile labels and icons, bar buttons, size values (body 28px, tiles 40px, buttons 72px) and the short list of plain-language messages (offline, printer needs paper or ink, new device blocked, download checked and safe, sent to the printer, turn off confirmation, help).

- [ ] **Step 1: Observe her:** note what she does on her computer today and her Windows habits (double-clicking icons, the X to close, Ctrl+C/V, right-click, the Start menu), whether she double-clicks, which text size is comfortable (print a sample at 24/28/36pt), pointer speed, her name and the words she uses for things.
- [ ] **Step 2: Write `ux-spec.md`** with the five tiles, the bottom bar, the size values and the message wording, following spec section 7.1.
- [ ] **Step 3: Show her a picture of Home** and ask where she'd click to read email, open Facebook, write a letter, print it and get help. Adjust labels or icons until she picks right each time.
- [ ] **Step 4: Commit** `docs: UX spec`.

### Task 2: Base OS, accounts, snapshots

**Files:** Create `scripts/01-base.sh`, `verify/checks/01-base.sh`

**Interfaces:** Produces users `grandma` (non-sudo, autologin) and `admin` (sudo); snapper configured for `/` with an apt pre/post hook; `nightly-reboot.timer` (04:00); unattended-upgrades enabled.

- [ ] **Step 1: Write the check:** `id grandma` exists and is not in `sudo`/`adm`; SSH server and Bluetooth inactive and disabled; `passwd -S root` shows `L`; `snapper list` works and an `apt install` of a no-op package creates a pre/post pair; `nightly-reboot.timer` and unattended-upgrades enabled.
- [ ] **Step 2: Run `verify/run.sh --only 01`; expected FAIL.**
- [ ] **Step 3: Implement `01-base.sh`** (idempotent user creation; autologin straight to the shell (no login screen); quiet boot with the boot menu hidden; apt hook calling `snapper create --type pre/post`).
- [ ] **Step 4: Re-run; expected PASS.** Reboot; confirm auto-login. Test rollback: install a package, `snapper rollback`, reboot, package gone. Record boot-fallback steps in the runbook.
- [ ] **Step 5: Commit** `feat: base OS, accounts, snapshots`.

### Task 3: Network and remote access

**Files:** Create `scripts/02-network.sh`, `scripts/03-remote.sh`, `verify/checks/02-network.sh`, `verify/checks/03-remote.sh`

**Interfaces:** `ufw` per Global Constraints; system DNS Quad9; Tailscale joined with SSH enabled (key from `TAILSCALE_AUTHKEY`); RustDesk reachable only via the tailnet.

- [ ] **Step 1: Write checks:** `ufw status verbose` contains `Default: deny (incoming)`; `ss -tlnp` shows no non-loopback listeners (Tailscale SSH excluded); `resolvectl status` shows `9.9.9.9`; `tailscale status` shows the device online; admin can `tailscale ssh admin@<host>` from another machine (manual step).
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement.** Pre-load her home Wi-Fi (NetworkManager profile from `WIFI_SSID`/`WIFI_PSK`, autoconnect). Outgoing: allow 80/443, 53, 123, Tailscale and RustDesk requirements, health-check host; default deny outgoing last. RustDesk spike: confirm unattended screen access works over the tailnet; if not, document the chosen alternative.
- [ ] **Step 4: Re-run; expected PASS.** Reboot and confirm SSH and screen access without anyone logging in manually.
- [ ] **Step 5: Commit** `feat: firewall, filtering DNS, remote access`.

### Task 4: Kernel, mount and AppArmor hardening

**Files:** Create `hardening/sysctl.conf`, `hardening/modprobe-blacklist.conf`, `hardening/fstab-mounts.txt`, `scripts/04-hardening.sh`, `verify/checks/04-hardening.sh`

**Interfaces:** Produces `/etc/sysctl.d/99-senior.conf`, `/etc/modprobe.d/senior-blacklist.conf` (FireWire, Thunderbolt, unused filesystems and `usb-storage`), `noexec,nosuid,nodev` mounts, AppArmor enabled and enforcing.

- [ ] **Step 1: Write the check:** `sysctl kernel.kptr_restrict` and `kernel.dmesg_restrict` >= 1, `kernel.unprivileged_bpf_disabled` = 1; `lsmod` shows none of the blacklisted modules; `findmnt /tmp /home` show `noexec`; `aa-status` reports enforce mode.
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement `04-hardening.sh`** using Kicksecure-style values as reference (record any value skipped for compatibility and why). Verify `/home` noexec does not break Firefox profiles (Firefox runs from `/usr`).
- [ ] **Step 4: Re-run; expected PASS.** Run `lynis audit system`, record the baseline score.
- [ ] **Step 5: Commit** `feat: kernel, mount and AppArmor hardening`.

### Task 5: Browser policies, allow-list and confinement

**Files:** Create `browser/policies.json.tmpl`, `browser/allowlist.txt`, `browser/blocked.html.tmpl`, `browser/firefox.apparmor`, `scripts/05-browser.sh`, `scripts/render_policies.py`, `tests/test_policies.py`, `verify/checks/05-browser.sh`

**Interfaces:** `render_policies(allowlist: list[str], admin_name: str) -> dict`; produces `/etc/firefox/policies/policies.json` (root-owned) and `/usr/local/share/senior-laptop/blocked.html`; `allowlist.txt` one domain per line.

- [ ] **Step 1: Write `tests/test_policies.py`:** valid JSON; `WebsiteFilter.Block == ["<all_urls>"]` and `Exceptions` contains every allow-list domain; `ExtensionSettings` force-installs `uBlock0@raymondhill.net` locked; `DisableDeveloperTools`, `DisablePrivateBrowsing`, `BlockAboutConfig` true; `Preferences` sets `layout.css.devPixelsPerPx` 1.3, `full-screen-api.enabled` false, `network.trr.mode` 5.
- [ ] **Step 2: Run `pytest tests/test_policies.py`; expected FAIL.**
- [ ] **Step 3: Implement the template and `render_policies`.** Seed `allowlist.txt` with `mail.google.com`, `accounts.google.com`, `docs.google.com`, `drive.google.com`, `*.gstatic.com`, `*.googleusercontent.com`, `facebook.com`, `*.fbcdn.net`; block page uses `{ADMIN_NAME}` and `{ADMIN_PHONE}` and the shell theme; enable the uBlock Origin Annoyances/cookie filter lists through managed storage and set `print.always_print_silent` true.
- [ ] **Step 4: Run the tests; expected PASS.**
- [ ] **Step 5: Confinement spike:** write `firefox.apparmor` (read/write only the profile dirs and `~/Downloads`; deny `~/` otherwise). Try Flatpak Firefox as the alternative and record whether `policies.json` is honoured. Pick one in the runbook.
- [ ] **Step 6: On the laptop, write the check and installer;** sign in to Gmail, Docs and Facebook as grandma, add every domain that triggers a block page to `allowlist.txt`, confirm `https://example.com` shows the block page, and confirm Firefox cannot read `~/.ssh` or another home directory path (AppArmor denial in `aa-status`/`dmesg`).
- [ ] **Step 7: Commit** `feat: Firefox policies, allow-list and confinement`.

### Task 6: Download airlock

**Files:** Create `airlock/airlock.py`, `airlock/airlock.service`, `scripts/06-airlock.sh`, `tests/test_airlock.py`, `verify/checks/06-airlock.sh`

**Interfaces:**
- `class Verdict(Enum): CLEAN, INFECTED, BLOCKED_TYPE, SCAN_ERROR, INCOMPLETE`
- `def classify(path: Path) -> str | None`: one of `pdf, doc, docx, jpg, png, txt` from `file --mime-type`, else `None`.
- `def scan(path: Path) -> Verdict`: `clamdscan --fdpass`; `SCAN_ERROR` if `clamd` unreachable.
- `def process(path: Path, downloads_dir: Path, notify: Callable[[str, str], None]) -> Verdict`.
- Quarantine dir `/var/lib/senior-laptop/quarantine` (owned by `airlock`, unreadable by grandma); watcher is a systemd service using `inotifywait` on `close_write`/`moved_to`, confined by AppArmor.

- [ ] **Step 1: Write failing tests** (scan stubbed): `classify` returns `"pdf"` for real PDF bytes and `None` for an ELF renamed `x.pdf`; `process` ignores `*.part` and zero-byte files (`INCOMPLETE`); `Résumé final.pdf` is delivered intact; a clean PDF is moved and `notify("Checked and safe", ...)` called; EICAR (two split string literals) returns `INFECTED`, is deleted and the admin alert called; with the scan stub raising `ConnectionError`, `process` returns `SCAN_ERROR`, leaves the file quarantined and notifies with the ask-for-help message.
- [ ] **Step 2: Run `pytest tests/test_airlock.py`; expected FAIL.**
- [ ] **Step 3: Implement to the interfaces;** atomic `os.replace` after a size-stable check; `notify` uses `notify-send` for her and the Task 9 alert helper for the admin.
- [ ] **Step 4: Run the tests; expected PASS.**
- [ ] **Step 5: On the laptop:** install `clamav-daemon`, enable `freshclam`, enable the service; check downloads an EICAR file through Firefox (temporarily allow-listed test URL) and verifies it never reaches `~/Downloads`; a clean PDF does; stopping `clamav-daemon` leaves a PDF quarantined with the help message.
- [ ] **Step 6: Memory check:** with Firefox open and `clamd` running, `free -m` shows >= 1000MB available (8GB) or >= 500MB with zram (4GB).
- [ ] **Step 7: Commit** `feat: download airlock with ClamAV`.

### Task 7: Custom shell (Home, bottom bar, messages)

**Files:** Create `shell/shell.py`, `shell/home.py`, `shell/bar.py`, `shell/help.py`, `shell/messages.py`, `shell/copy.py`, `shell/tiles.json`, `shell/theme.css`, `shell/sway.conf`, `shell/shell.desktop`, `tests/test_shell.py`, `verify/checks/07-shell.sh`

**Interfaces:**
- `def load_tiles(path: Path) -> list[Tile]`, `Tile = {label: str, command: list[str], icon: str}`; order: Email, Facebook, Write a Letter, My Downloads, Help.
- `copy.COPY: dict[str, str]`: all user-facing text, in plain words, from `docs/ux-spec.md`.
- `def connectivity_message() -> str | None`: `None` online, else `COPY["offline"]`.
- `def printer_message() -> str | None`: maps CUPS reasons (`media-empty`, `marker-supply-low`, `offline`) to `COPY["printer_paper_ink"]` etc.
- `def usb_blocked_message() -> str | None`: `COPY["new_device_blocked"]` when USBGuard has blocked an input device.
- `class ClickDebouncer(window_ms: int = 600)` with `accept(now_ms: int) -> bool`: false for a second click inside the window.
- Compositor: `sway`; all windows maximized, no decorations, window-closing and fullscreen shortcuts (Ctrl+W, Ctrl+Q, Alt+F4, F11) removed; Ctrl+C/V/X/Z/A and other editing shortcuts keep working.

- [ ] **Step 1: Write failing tests in `tests/test_shell.py`:** `load_tiles` returns exactly the five labels in order with non-empty commands; `ClickDebouncer` accepts the first click, rejects a second at +300ms and accepts one at +700ms; `connectivity_message`, `printer_message` and `usb_blocked_message` return the `COPY` strings for stubbed states.
- [ ] **Step 2: Run `pytest tests/test_shell.py`; expected FAIL.**
- [ ] **Step 3: Implement** to the interfaces. Home: greeting with her name (from `config.env`), large date and time, five tiles, and a "Turn off" button that asks once ("Turn off" / "Keep working"). Bottom bar laid out like the Windows taskbar and always visible: Home at the far left, then Back, Print, Volume (- and +) and Help, with the clock at the right; Home closes the open app. A double-click on a tile works but opens one window; right-click does nothing. Print sends Ctrl+P with Firefox set to print silently to the default printer, then shows `COPY["print_sent"]`. Help shows `{ADMIN_NAME}`, `{ADMIN_PHONE}` and "Connected for support" (Tailscale online). Messages are large and go away on click. Email opens the Google kiosk window at Gmail; Write a Letter opens it at Docs; Facebook opens its own profile; My Downloads opens a Downloads-only viewer; a tile focuses an existing window instead of opening a second one.
- [ ] **Step 4: Run the tests; expected PASS.** `xvfb-run python3 shell/shell.py --selftest` exits 0.
- [ ] **Step 5: On the laptop:** autostart the shell; the check confirms it runs after boot with no login screen or stock panel; click through the core tasks (email, Facebook, write and print a letter, Help, Turn off) with the mouse only; confirm a double-click on a tile opens one window; confirm no Firefox prompt or cookie banner appears on first load of Gmail and Facebook (add the uBlock Annoyances lists in Task 5 if one does).
- [ ] **Step 6: Commit** `feat: custom shell`.

### Task 8: Desktop lockdown, clean-slate boot, printing and USBGuard

**Files:** Create `scripts/07-desktop.sh`, `scripts/08-printing-usb.sh`, `hardening/usbguard-rules.tmpl`, `verify/checks/08-desktop.sh`, `verify/checks/09-printing-usb.sh`

**Interfaces:** Consumes `PRINTER_NAME` and the printer's make/model (**open**). Produces: panel and menus stripped; no terminal or console shortcuts; root-owned read-only desktop configs; `clean-slate.service` clearing cache/temp each boot; default CUPS printer `Home-Printer` (admin-only); USBGuard rules generated from currently attached mouse, keyboard and printer.

- [ ] **Step 1: Identify the printer** (make/model from its label; `lsusb`; `ipptool` against `ipp://localhost:60000/ipp/print` for driverless; `lpinfo -v`). Choose per spec 6.7 order and record in the runbook.
- [ ] **Step 2: Write checks:** terminal binaries absent for grandma; config files not writable by grandma; console-switch and terminal shortcuts absent from the compositor config; `lpstat -d` shows `Home-Printer`, a test job completes, `grandma` cannot run `lpadmin`; `usbguard list-devices` shows only mouse, keyboard and printer allowed; a spare USB stick plugged in is blocked (manual, recorded); after reboot the browser cache directory is empty.
- [ ] **Step 3: Run; expected FAIL.**
- [ ] **Step 4: Implement.** Remove packages rather than hiding icons; `chown root` + `chmod a-w` configs; clean-slate service on boot; USBGuard `generate-policy` from the attached devices; **recovery path:** an admin-only `usbguard allow-device` runbook entry, plus a Home message when a new input device is blocked ("A new device was blocked. Ask {ADMIN_NAME}.").
- [ ] **Step 5: Re-run; expected PASS.** Test empty-tray printing and confirm Task 7's `printer_message()` text. Unplug the mouse, plug in a different one, confirm it is blocked and the message appears, then re-allow via the runbook.
- [ ] **Step 6: Commit** `feat: desktop lockdown, printing, USBGuard`.

### Task 9: Updates, monitoring and alerts

**Files:** Create `scripts/09-updates-monitoring.sh`, `verify/checks/10-monitoring.sh`

**Interfaces:** Produces `senior-laptop-heartbeat.timer` (every 5 minutes) pinging `HEALTHCHECK_URL`; `/usr/local/bin/senior-laptop-alert "<message>"` used by Tasks 6 and 8; failed-update alert hook.

- [ ] **Step 1: Write the check:** heartbeat timer active; health-check URL returns 200; `senior-laptop-alert "test"` reaches the admin (manual confirmation recorded); a forced failure of `unattended-upgrade` triggers the alert.
- [ ] **Step 2: Run; expected FAIL.**
- [ ] **Step 3: Implement.** Disconnect Wi-Fi for 15 minutes and confirm the heartbeat service alerts the admin; reconnect and confirm it recovers.
- [ ] **Step 4: Re-run; expected PASS.**
- [ ] **Step 5: Commit** `feat: updates, monitoring and alerts`.

### Task 10: Google account security, audit, rebuild and usability

**Files:** Create `verify/checks/99-acceptance.sh`; extend `docs/runbook.md`

- [ ] **Step 1: Google account:** turn on 2-step verification with admin-held recovery options (backup codes stored by the admin, recovery email/phone set), and the same for Facebook; record the steps in the runbook, never the codes.
- [ ] **Step 2: Encode spec section 9** as checks not already covered (non-allow-listed site blocked; fullscreen fake-alert page blocked; Firefox cannot read outside Downloads); manual items go in a pass/fail table in the runbook.
- [ ] **Step 3: Audit:** run `lynis audit system` (index >= 80) and an OpenSCAP scan with the closest available profile; from another machine, boot a Kali live USB and run `nmap -p- <LAN address>` and `nmap -p- <tailnet address>`; expected no open ports. Record the findings and fix or justify each high item.
- [ ] **Step 4: Run `provision.sh` on a fresh install, then `verify/run.sh`; expected all PASS.** Reboot and confirm Home loads, remote access reconnects and timers are active.
- [ ] **Step 5: Rebuild test:** reinstall from the runbook and scripts, time it (target under one hour); create the golden disk image and store it off the device.
- [ ] **Step 6: Usability test with her (spec 7.3):** with one sentence of introduction she reads an email, opens Facebook, writes and prints a letter, finds Help and turns it off, without help. Fix anything she stumbles on and re-test; check again after one week.
- [ ] **Step 7: Place the printed "No one from Microsoft, Apple or your bank will ever call..." card by the screen.**
- [ ] **Step 8: Commit** `docs: runbook and acceptance results`.

### Task 10b: Pre-delivery preparation and delivery day

**Files:** Modify `senior-laptop/docs/runbook.md` (add a delivery checklist)

- [ ] **Step 1: Collect from her before delivery:** home Wi-Fi name and password, Gmail and Facebook logins and a way to receive 2-step codes (or set recovery to the administrator), the printer (or its make and model), and a list of files on her old Windows computer.
- [ ] **Step 2: Sign in on the bench:** sign in to Gmail, Docs and Facebook in the kiosk profiles; turn on 2-step verification; reboot and confirm the sessions persist and every screen she will see is covered by the allow-list.
- [ ] **Step 3: Move her files:** upload her documents and photos from the old Windows computer to Google Drive, and leave the old computer untouched until she is comfortable.
- [ ] **Step 4: Printer:** install and test her printer (or its replacement) with real prints from Docs and Gmail.
- [ ] **Step 5: Burn-in:** run 48 hours with the health-check on; confirm no alerts, Conservation Mode on, and one update cycle completes with a snapshot.
- [ ] **Step 6: Delivery day:** place and plug in; press power; confirm Home appears and the laptop joins her Wi-Fi (if not, use the administrator recovery login to fix it); confirm remote access, print a test page, give the one-sentence introduction and leave the printed card.
- [ ] **Step 7: One week later:** remote check-in and a phone call; fix anything she stumbled on.
- [ ] **Step 8: Commit** `docs: delivery checklist`.

---

### Optional extras (build only if approved after Task 10)

**Task 11: Read-only root with overlay.** Check: writes to `/usr` fail for root while mounted read-only; Task 2's update flow gains an admin `senior-laptop-unlock` script (remount rw, update, reboot). Verify updates and rollback still work.

**Task 12: DNS allow-list.** Local resolver answering only for `allowlist.txt` domains (NXDOMAIN otherwise). Check: allow-listed name resolves, `example.com` returns NXDOMAIN, and the Gmail/Docs/Facebook sign-in flows still work; record any extra CDN domains needed.

## Self-review notes
- Spec coverage: 6.1->Tasks 1-2, 6.2->Task 5, 6.3->Tasks 4/8, 6.4/6.5->Task 3, 6.6->Task 6, 6.7->Task 8, 6.8->Tasks 2/9/10, 6.9->Task 10, UX->Tasks 1b, 7 and 10, optional extras->Tasks 11-12.
- Open items stay explicit: printer model (Task 8), RAM slot and Wi-Fi chip (Task 1), TPM unlock (Task 1), Flatpak vs AppArmor (Task 5), RustDesk viability (Task 3), allow-list contents (Task 5), ADMIN_NAME/ADMIN_PHONE (config).
- Pure logic (`classify`, `process`, `load_tiles`, policy rendering) is unit-tested off-device; hardware-dependent steps run on the laptop.
