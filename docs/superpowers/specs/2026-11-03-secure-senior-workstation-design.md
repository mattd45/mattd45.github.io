# Product Design Document (PDD) v3: Secure Senior-Friendly Laptop Workstation

Status: DRAFT for review. Supersedes v2 (Raspberry Pi) and the original PDF PDD.
Date: 2026-11-04

## 1. Executive Summary & Objective

Design, provision and deploy a locked-down, single-purpose computing appliance for one elderly family member who is vulnerable to online scams. A refurbished/new-old-stock laptop runs a hardened Debian system that exposes only: Email (Gmail), Google Docs (for writing), Facebook, a Downloads folder, printing, and a Help button. The administrator supports it remotely with no open inbound ports.

### 1.1 Success criteria
- She cannot install software, open a terminal, change system settings, or reach an admin account.
- She can visit only allow-listed websites; every other destination shows a friendly block page.
- Every download is scanned before she can open it.
- Nothing listens for inbound connections from the network; unknown USB devices do nothing.
- The administrator can connect remotely after any reboot.
- A bad update or breakage can be rolled back; the device can be rebuilt from a script in under an hour.
- Her writing lives in Google Drive (Docs), so there is no local document store to lose.
- She finds it easy and pleasant to use with no training (section 7).

## 2. Threat Model

The primary threat is **social engineering**: fake tech-support calls and pop-ups, phishing emails, Facebook scams, being talked into granting access or installing software. The design removes anything she could be talked into doing, and does not rely on "Linux is immune to Windows-targeted scams".

Secondary threats: malicious downloads/attachments, browser exploits, malicious USB devices, unattended software rot, Google account takeover, a bad update.

Out of scope: a determined attacker with long-term physical access; targeted nation-state attacks.

## 3. Personas
- **Primary user:** elderly family member (`grandma` account), minimal technical literacy, **mouse and keyboard** user.
- **Administrator:** technical family member supporting the device remotely.

## 4. Scope

### 4.1 In scope
- **Hardware:** Lenovo IdeaPad 3 15ADA05 (model 81W1: Ryzen 3, 4GB RAM, 128GB SSD, 15.6" FHD TN, 2-cell battery), listed at £125 on Facebook Marketplace. RAM to be upgraded to 8GB if the spare slot is confirmed. The built-in battery acts as a short-term UPS; battery charge limited to ~80% ("Conservation Mode"). Existing monitor/keyboard/mouse may be used (open item).
- **OS:** Debian stable, minimal desktop, Windows fully wiped.
- **Accounts:** standard non-sudo `grandma`; separate `admin`.
- **Apps:** Gmail and Google Docs (Firefox ESR kiosk window "Google"), Facebook (separate kiosk window and profile), Downloads folder, Print, Help. **No office suite installed** (removes macro and document-parser attack surface).
- **Custom, simple UI** built on proven design rules for older users (section 7).
- **Browser allow-list**, uBlock Origin enforced, download scanning.
- **Hardening layers:** per-app confinement, USBGuard, AppArmor, BIOS/Secure Boot/TPM disk encryption, kernel and mount hardening, btrfs snapshots with rollback, clean-slate-on-boot, hardening audit.
- **Network:** restrictive firewall, filtering DNS, remote management via Tailscale (SSH) and RustDesk (screen).
- **Printing:** CUPS, USB printer (model TBD).
- **Google account security:** 2-step verification with admin-managed recovery.

### 4.2 Out of scope
- Windows apps / `.exe` / `.msi`; local office suite.
- Local document storage beyond Downloads (Docs live in Google Drive).
- Complex multitasking; multi-user switching.
- Video calls (deferred; webcam/mic not enabled in v3).

### 4.3 Optional extras (built only if approved after the core is working)
- Read-only root filesystem with writable overlay.
- DNS allow-list: local resolver answering only for allow-listed domains.

## 5. Architecture

```
+-------------------------------------------------------------------+
|                           Laptop (Debian)                         |
|  +-----------------------------+   +---------------------------+  |
|  | grandma (standard user)     |   | Hardened system layer     |  |
|  |  - Custom shell + Home      |   |  - ufw (restrictive)      |  |
|  |  - Firefox ESR kiosk x2     |   |  - filtering DNS          |  |
|  |    (Google | Facebook)      |   |  - AppArmor, USBGuard     |  |
|  |    confined, uBlock locked  |   |  - kernel/mount hardening |  |
|  |  - Downloads folder         |   |  - btrfs snapshots        |  |
|  +--------------+--------------+   |  - ClamAV + airlock       |  |
|                 |                  |  - CUPS (admin only)      |  |
|        Quarantine -> scan          |  - unattended upgrades    |  |
|                 -> Downloads       +-------------+-------------+  |
+-------------------------------------------------|-----------------+
                                                  | outbound only
                      Tailscale SSH / RustDesk / health-check ping
                                    ^
                          Administrator (remote)
```

## 6. Technical Specification

### 6.1 Firmware and disk
- Wipe Windows; update BIOS; set a BIOS supervisor password; lock boot order (no USB boot after install); Secure Boot enabled; Lenovo Conservation Mode on.
- Full-disk encryption (LUKS2 on btrfs) with TPM2 auto-unlock (`systemd-cryptenroll`). If AMD fTPM unlock proves unreliable on this laptop, fall back to no disk encryption plus the BIOS lock (theft is a low risk compared to the maintenance burden of a boot passphrase); decision recorded in the runbook.
- btrfs subvolumes for root and home; snapper snapshots before and after each apt run; documented rollback procedure including a boot fallback.

### 6.2 Browser (Firefox ESR, policy-enforced, confined)
- Root-owned `policies.json`; **domain allow-list** for Gmail/Google sign-in, Google Docs/Drive, Facebook and required CDN domains. Everything else renders the friendly block page: "That page isn't available. Tap Help and {ADMIN_NAME} will sort it out."
- uBlock Origin force-installed and locked.
- Disabled: fullscreen, devtools, private browsing, `about:config`, add-on installs, notifications, `file://`, password export, DNS-over-HTTPS, pop-ups.
- Kiosk presentation: no address bar/tab strip, default zoom ~130%, one window and profile per app group (Google; Facebook).
- Confinement: AppArmor-enforced Firefox profile limiting file access to its profile and the Downloads folder; Flatpak Firefox evaluated as an alternative in a spike (policy support must be confirmed).
- Facebook is the riskiest allowed app: 2FA with admin-managed recovery.

### 6.3 OS lockdown
- Remove (not just hide) terminal, settings panels, package-manager GUIs, and any file manager except a Downloads viewer. Remove terminal and console-switching shortcuts.
- Desktop, panel and policy configs are root-owned and read-only to `grandma`.
- Disable: SSH server (Tailscale SSH instead), VNC, Bluetooth (if unused), root login, USB storage.
- **USBGuard:** default block; allow-list only her mouse, keyboard and printer by device ID.
- **Kernel and mount hardening:** Kicksecure-style sysctl settings and boot parameters; blacklist unused modules (FireWire, Thunderbolt, etc.); `noexec,nosuid,nodev` on `/tmp`, `/home` and the download directories.
- **AppArmor** enforced for Firefox and the airlock.
- **Clean slate on boot:** browser cache, temporary files and session junk reset every boot; logins and Downloads persist.
- Auto-login to `grandma`; no lock screen; no unexpected sleep.

### 6.4 Network
- `ufw`: default deny incoming; outgoing limited to web (80/443), DNS, NTP and what Tailscale, RustDesk and the health-check require (exact list derived in prototype).
- Filtering DNS (Quad9) system-wide; browser DoH disabled.

### 6.5 Remote administration
- **Tailscale** with Tailscale SSH (key-based, no inbound ports) as the primary admin path; separate `admin` account for escalation.
- **RustDesk** (or equivalent) for screen sharing; access limited to the tailnet. To be verified on the laptop.
- Screen sharing needs an active session, hence auto-login.

### 6.6 Downloads: scan every one (the "airlock")
1. Firefox saves to a quarantine folder `grandma` cannot open.
2. A watcher runs `clamdscan` and a MIME-type check (never the extension).
3. Clean and allowed: moved to `~/Downloads`, friendly notice "Checked and safe".
4. Infected, disallowed or un-scannable: not delivered; infected/disallowed are deleted and the admin is alerted; un-scannable stays quarantined with a "please ask {ADMIN_NAME}" message.
5. Allowed types: PDF, DOC/DOCX, JPG/PNG, TXT (Word files are opened by uploading to Google Docs). Blocked: executables, scripts, installers, archives, ODT.
6. Limitation: ClamAV catches known malware only; scam documents are handled by the file-type limits and allow-list.

### 6.7 Printing
- CUPS, admin-managed only. **USB printer, model TBD.** x86 gives a wider driver choice: driverless (`ipp-usb`), then `hplip` / `epson-inkjet-printer-escpr` / `gutenprint` / Brother or Canon packages, else replace with a driverless IPP Wi-Fi printer.
- Printing happens from the browser (Google Docs, Gmail); fault states mapped to plain-language Home messages.

### 6.8 Updates, recovery and monitoring
- Unattended security upgrades for OS and browser, snapshot before each, nightly reboot window.
- Health-check heartbeat (e.g. healthchecks.io); admin alerted when it goes quiet or updates fail.
- Rebuild from scripts plus a golden disk image stored off the device.
- Documents are in Google Drive; Google account recovery details held by the administrator.

### 6.9 Hardening audit
- `lynis` and an OpenSCAP scan run during acceptance; target Lynis hardening index >= 80 and no unexplained high findings.
- Attack-test from a separate machine (Kali live USB): `nmap` of the LAN address and tailnet address shows no open ports.

## 7. Usability and UI

**Goal:** she can use it without being taught. We use long-established guidelines for older users (large type, high contrast, big click targets, few choices, plain words, the same layout everywhere, no hidden menus), not anything novel.

### 7.1 Rules
1. **Big:** text at least 28px, tile labels 40px, buttons at least 72px tall, large mouse cursor.
2. **High contrast:** dark text on a light background.
3. **Few choices:** Home shows five big tiles and nothing else: Email, Facebook, Write a Letter, My Downloads, Help.
4. **Plain words and a picture on every button,** in her own words ("Write a Letter", not "Documents").
5. **One click for everything.** Double-clicks are ignored so they can't do things twice.
6. **Same layout everywhere.** A bottom bar is always visible: Back, Home, Print, Volume, Help.
7. **Nothing happens unasked.** No update prompts, pop-ups or cookie banners. Messages are large, calm, in plain words, and go away on click.
8. **Hard to break.** Home always gets her back to the start. Turning off asks once ("Turn off" / "Keep working").
9. **Orientation:** Home shows a greeting with her name and the date and time in large type.
10. **A printed card** by the screen: three pictures, three lines, plus "No one from Microsoft, Apple or your bank will ever call. Hang up and call {ADMIN_NAME}. If anything looks wrong, switch it off."

### 7.2 What we build
A small custom shell (Home screen, bottom bar, plain-language messages, Help screen) that starts automatically at boot with no login screen. Gmail/Docs and Facebook open in Firefox kiosk mode (no browser controls). The block page uses the same look. The content of Gmail, Docs and Facebook pages belongs to Google and Facebook and can't be changed; the shell frames it and uBlock Origin's annoyance lists hide cookie banners.

### 7.3 Testing with her
- **Before building:** show her a picture of the Home screen and ask where she would click to read email, open Facebook, write a letter, print it, and get help. Change labels or icons until she picks right each time.
- **Acceptance:** with one sentence of introduction, she reads an email, opens Facebook, writes and prints a letter, finds Help, and turns it off, without help. Anything she stumbles on gets fixed. Check again after one week.

## 8. Open-Source Components

| Need | Component |
|---|---|
| Download scanning | ClamAV |
| Browser policy | Firefox ESR, Mozilla policy-templates, uBlock Origin |
| Hardening reference | Kicksecure (settings), CIS benchmarks |
| USB control | USBGuard |
| Access control | AppArmor |
| Snapshots | btrfs, snapper |
| Remote access | Tailscale, RustDesk |
| Printing | CUPS, ipp-usb |
| Audit | lynis, OpenSCAP, nmap (from a Kali live USB) |

## 9. Acceptance Tests (before handover)
- Cannot install a package, open a terminal, or reach settings.
- Non-allow-listed site shows the friendly block page; fullscreen fake-alert page is blocked.
- Unknown USB stick is ignored; printer works.
- EICAR test file is caught by the airlock; a clean PDF is delivered; with the scanner stopped, files stay quarantined.
- Browser cannot read files outside Downloads.
- Snapshot rollback works; rebuild from scripts and image succeeds.
- Reboot, then confirm remote SSH and screen access.
- Lynis and nmap results meet 6.9.
- Usability test with her passes (section 7.3).

## 10. Open Items / Placeholders
- Confirm the laptop's spare RAM slot and Wi-Fi chip (Linux support) before or at purchase.
- Printer make/model (USB).
- {ADMIN_NAME} and {ADMIN_PHONE}.
- Her vision/hearing/mouse-control needs (found in the observation step), her preferred name for the greeting, and whether she uses the laptop screen or the existing monitor (and where the laptop sits).
- What the laptop does when the lid is closed.
- sway vs labwc as the base compositor, and which window-closing shortcuts can be removed (Task 7 spike).
- Whether TPM auto-unlock works on this laptop (else no disk encryption).
- Flatpak vs AppArmor-confined Firefox (spike result).
- Exact firewall rules and Gmail/Docs/Facebook domain list (derive in prototype).
- Approve or decline the optional extras (4.3).
