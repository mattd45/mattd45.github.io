# Runbook

Authored in the cloud; everything under "Device checklist" must be done on the laptop or with her.
See the plan (`docs/superpowers/plans/2026-11-03-secure-senior-workstation.md`) for the numbered tasks.

## Device checklist (device-pending)
- [ ] Task 1: purchase checks, BIOS update/password, wipe Windows, install Debian (LUKS2 + btrfs), TPM unlock spike; record OS, kernel, Wi-Fi chip, RAM here.
- [ ] Task 1 step 3, purchase checklist: photos of the laptop with the serial matching the box; powers on; keyboard, USB ports and Wi-Fi work; battery holds charge; no BIOS password or locks; confirm the spare RAM slot; pay cash on collection.
- [ ] Task 1b: observe her (habits, text size, pointer speed, her name); show her a picture of Home and check where she'd click; update `docs/ux-spec.md`.
- [ ] Task 2: run `provision.sh --only 01`, `verify/run.sh --only 01`; confirm the `greetd` package exists on the chosen Debian; reboot and confirm auto-login with no login screen; snapshot rollback test (install a package, `snapper rollback`, reboot) and write the boot-fallback steps here.
- [ ] Task 3: Wi-Fi saved and joins on its own; `verify --only 02,03`; Tailscale apt URLs from memory (check against tailscale.com docs); RustDesk spike (unattended screen access over the tailnet; set `RUSTDESK_DEB`); admin `tailscale ssh` from another machine.
- [ ] Task 4: `verify --only 04`; `lynis audit system` baseline score; confirm Firefox runs from a noexec `/home`; confirm `/home` is a btrfs subvolume `@home` (fstab line assumes it).
- [ ] Task 5: `about:policies` shows the policies (which of `/etc/firefox/policies` or the `distribution` dir is read); uBlock filter-list IDs; sign in to Gmail, Docs and Facebook as grandma and extend `browser/allowlist.txt` for every blocked domain; confirm what Firefox's built-in "Blocked Page" looks like to her; run Firefox a week in AppArmor complain mode, review with `aa-logprof`, then enforce.
- [ ] Task 6: `verify --only 06` (EICAR through ClamAV; delete `~grandma/Downloads/clean-check.pdf` afterwards); `free -m` with Firefox and clamd running; real Firefox download lands in quarantine then Downloads.
- [ ] Task 7: shell has only been syntax-checked (GTK cannot load in the build container): run it on the laptop, click every tile and bar button by mouse, confirm a double-click opens one window, Back/Print (wtype) and Volume (wpctl) work, Turn off asks once, toasts appear (spool, offline, printer, new device); confirm sway `nop` binds really stop Ctrl+W/Ctrl+Q/F11; confirm xkb layout `gb` matches her keyboard; confirm the `internal:` tiles and Downloads viewer open a PDF via `file://`.
- [ ] Task 8: identify the printer (make/model, `lsusb`, `driverless`, `lpinfo -v`) and pick the driver per spec 6.7; plug in her mouse, keyboard and printer, then run `provision.sh --only 08`; `verify --only 08,09`; printed test page; a spare USB stick must not mount; an unknown USB mouse must be blocked and the shell must toast "A new device was blocked" (the `usbguard watch` output format is from memory: check `usb_blocked_flag` fires). Admin recovery: `usbguard list-devices -b`, `usbguard allow-device <id> -p`. Replacing her mouse later means re-running step 08 with it plugged in.
- [ ] Task 9: create a healthchecks.io check (5-minute period, ~15-minute grace, email to the admin) and put its URL in `config.env`; `verify --only 10`; `senior-laptop-alert "test"` reaches the admin; Wi-Fi off for 15 minutes raises the alert and turning it back on clears it; confirm a stopped `clamav-daemon` triggers an OnFailure alert.

## Order of work
Buy and inspect (Task 1) -> install Debian, set BIOS password -> `provision.sh` (scripts 01-09) -> `verify/run.sh` -> sign in and tune the allow-list (Task 5) -> printer and USBGuard (Task 8, with her devices plugged in) -> audit (below) -> usability test (below) -> delivery (below).

## Google and Facebook account security (Task 10 step 1)
- Turn on 2-step verification for her Google and Facebook accounts; keep the backup codes and recovery email/phone with the administrator (never in this repo).
- Add the administrator as a recovery contact where the service allows it; check "recent security activity" on both accounts.

## Audit (Task 10 step 3)
1. On the laptop: `sudo lynis audit system`; record the hardening index (target >= 80) and fix or justify each high finding. `verify/checks/99-acceptance.sh` repeats this check.
2. From another machine on her network, boot a Kali live USB and run `nmap -p- <laptop LAN IP>` and, over Tailscale, `nmap -p- <laptop tailnet IP>`; expected: no open TCP ports (the tailnet shows only what Tailscale offers). Also `nmap -sU --top-ports 100 <laptop LAN IP>` and note any open UDP port.
3. Run an OpenSCAP scan with the closest available profile and record the findings here.

## Manual acceptance (spec section 9)
| Test | Result |
|---|---|
| Install a package, open a terminal, reach settings: all impossible | |
| A non-allow-listed site shows the blocked page; a fullscreen fake-alert page is blocked | |
| Unknown USB stick ignored; printer works; unknown USB mouse blocked with a message | |
| EICAR caught; clean PDF delivered; scanner stopped leaves files held with a message | |
| Firefox cannot read files outside Downloads (check `dmesg`/AppArmor log) | |
| Snapshot rollback works; rebuild from scripts and the golden image succeeds | |
| After a reboot: Home loads, Tailscale SSH and screen access work | |

## Admin recovery (consoles are masked)
- **Remote:** `tailscale ssh admin@senior-laptop`. If her Wi-Fi fails, turn on the phone hotspot saved as `HOTSPOT_SSID`; the laptop joins it and you can fix her Wi-Fi remotely (`nmcli`).
- **Local (no network at all):** BIOS password, then at boot hold Shift for GRUB, press `e`, append `init=/bin/bash` to the `linux` line, boot, `mount -o remount,rw /`, fix the problem, `exec /sbin/init`. (Root is locked, so rescue mode will not work; this is deliberate.)
- **Blocked mouse/keyboard:** `usbguard list-devices -b`, then `usbguard allow-device <id> -p`.
- **Rollback:** `snapper list`, `snapper rollback <number>`, reboot.

## Rebuild and golden image (Task 10 step 5)
After a clean install: `provision.sh`, `verify/run.sh`, then take an image of the disk (for example with `dd` or Clonezilla from a live USB) and store it off the laptop. Time a rebuild from the runbook; target under one hour.

## Usability test with her (spec 7.3)
1. Give one sentence of introduction ("Press the big button for what you want, and press Home to start again") and the printed card.
2. Ask her to: read an email, open Facebook, write a letter and print it, open a downloaded file, find Help, turn it off. Do not help.
3. Record per task: done unaided / needed a hint / failed, and what she said. Fix wording, sizes or flow and repeat until she does all of them unaided. Check again after one week.

## Delivery (Task 10b)
**Before delivery (on the bench)**
1. Collect: her home Wi-Fi name and password, Gmail and Facebook logins and a way to receive 2-step codes, her printer (or its model), and a list of files on her old Windows computer.
2. Sign in to Gmail, Docs and Facebook in the kiosk profiles as grandma; turn on 2-step verification; reboot and confirm the sessions persist and every screen she will see is covered by the allow-list.
3. Upload her documents and photos from the old computer to Google Drive; leave the old computer untouched until she is comfortable.
4. Install and test her printer (or its replacement) with real prints from Docs and Gmail.
5. Burn-in: 48 hours with the health-check on; no alerts, Conservation Mode on, one update cycle completed with a snapshot.

**Delivery day**
6. Place it, plug it in, press power: Home appears and it joins her Wi-Fi (if not, use the hotspot fallback). Confirm remote access, print a test page, give the one-sentence introduction and leave the printed card (`docs/printed-card.md`).

**One week later**
7. Remote check-in and a phone call; fix anything she stumbled on.
