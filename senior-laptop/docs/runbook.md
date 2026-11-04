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
