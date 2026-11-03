# Product Design Document (PDD) v2: Secure Senior-Friendly Raspberry Pi Workstation

Status: DRAFT for review. Supersedes the original PDD ("Secure_Senior_Workstation_PDD.pdf").
Date: 2026-11-03

## 1. Executive Summary & Objective

Design, provision and deploy a locked-down, single-purpose computing appliance for one elderly family member who is vulnerable to online scams. It replaces a mainstream desktop OS with a hardened Raspberry Pi OS system that exposes only: Email (Gmail), Facebook, word processing (LibreOffice Writer), a documents folder, printing, and a Help button. The administrator can support it remotely without port forwarding.

### 1.1 Success criteria
- She cannot install software, open a terminal, change system settings, or reach an admin account.
- She can only visit allow-listed websites; every other destination shows a friendly block page.
- Every download is scanned before she can open it.
- Nothing listens for inbound connections from the network.
- The administrator can connect remotely after any reboot.
- Her documents are backed up nightly to Google Drive.
- The device can be rebuilt from scratch from a script and a spare card in under an hour.
- She finds it easy and pleasant to use (validated with her, see section 9).

## 2. Threat Model (changed from v1)

The primary threat is **social engineering**, not malware: fake tech-support calls and pop-ups, phishing emails, Facebook scams, and being talked into granting access or installing software. The design therefore removes anything she could be talked into doing, and does not rely on "Linux is immune to Windows-targeted scams" (fake alerts and phone-number pop-ups work on any OS).

Secondary threats: malicious downloads/attachments, unattended software rot, MicroSD/storage failure, accidental self-misconfiguration.

Out of scope threats: a determined local attacker with physical access; targeted nation-state attacks.

## 3. Personas

- **Primary user:** elderly family member (`grandma` account), minimal technical literacy, needs a calm, predictable, uncluttered experience.
- **Administrator:** technical family member who supports the device remotely.

## 4. Scope

### 4.1 In scope
- Hardware: Raspberry Pi 4 or 5, **4GB RAM minimum** (ClamAV needs ~1GB), official PSU, boot from a USB SSD (preferred) or high-endurance MicroSD, plus a spare pre-flashed boot device.
- OS: Raspberry Pi OS (Desktop), hardened.
- Accounts: standard non-sudo `grandma`; separate `admin` account (strong password, key/remote only).
- Apps: Gmail and Facebook (Firefox ESR kiosk windows), LibreOffice Writer (macros disabled), Documents folder, printing, Help.
- Browser allow-list, uBlock Origin enforced, download scanning.
- Network: restrictive firewall, filtering DNS.
- Remote management via Raspberry Pi Connect (see 6.4).
- Google Drive backup via rclone.
- Printing via CUPS.
- Simple custom Home screen.

### 4.2 Out of scope
- Windows apps / `.exe` / `.msi`.
- Local file storage outside the Documents folder.
- Multitasking, multi-user switching.
- Video calls (deferred; webcam/mic not enabled in v2).

## 5. Architecture

```
+-------------------------------------------------------------------+
|                         Raspberry Pi                              |
|  +-----------------------------+   +---------------------------+  |
|  | grandma (standard user)     |   | Hardened system layer     |  |
|  |  - Home screen (launcher)   |   |  - ufw (restrictive)      |  |
|  |  - Firefox ESR kiosk        |   |  - filtering DNS          |  |
|  |    + uBlock Origin (locked) |   |  - root-owned policies    |  |
|  |  - LibreOffice Writer       |   |  - unattended upgrades    |  |
|  |  - Documents (backed up)    |   |  - ClamAV (clamd)         |  |
|  +--------------+--------------+   |  - download airlock       |  |
|                 |                  |  - CUPS (admin-managed)   |  |
|        Quarantine folder           |  - rclone nightly sync    |  |
|        -> scan -> Downloads        +-------------+-------------+  |
+-------------------------------------------------|-----------------+
                                                  | outbound only
                         Raspberry Pi Connect  /  Google Drive  /  health-check ping
                                    ^
                          Administrator (remote)
```

## 6. Technical Specification

### 6.1 Browser (Firefox ESR, policy-enforced)
- Root-owned `policies.json` (Mozilla enterprise policies); `grandma` cannot edit it.
- **Domain allow-list** for Gmail/Google sign-in, Facebook, and required CDN domains only. Everything else renders a friendly block page ("That page isn't available. Tap Help and [ADMIN_NAME] will sort it out.").
- uBlock Origin force-installed and locked (cannot be removed or disabled).
- Disabled: fullscreen, devtools, private browsing, `about:config`, extension/add-on installs, notifications, `file://`, password export, DNS-over-HTTPS (so filtering DNS cannot be bypassed), pop-ups.
- Kiosk presentation: no address bar or tab strip, default zoom ~130%, one window per app (separate profiles for Gmail and Facebook to be evaluated in prototype).
- Selected settings may be borrowed from arkenfox/user.js; the full template is NOT used because it breaks Gmail/Facebook logins.
- Facebook is the riskiest allowed app: enable 2FA with admin-managed recovery.

### 6.2 OS lockdown
- Remove (not just hide) terminal, settings panels, package-manager GUIs; file manager removed or restricted to Documents.
- Remove keyboard shortcuts for terminal and text-console switching.
- Panel, browser policy and launcher configs are root-owned and read-only to `grandma`.
- Disable: SSH, VNC, Bluetooth (if unused), root login, USB storage auto-mount. **USB printer class remains allowed.**
- Auto-login to `grandma`; no lock screen; no unexpected sleep; `enable-linger` for the Pi Connect session.
- LibreOffice macros disabled.
- Scanned/download directories mounted `noexec`.

### 6.3 Network
- `ufw`: default deny incoming; outgoing restricted to web (80/443), DNS, NTP and what Pi Connect / rclone / health-check require (exact list to be derived in prototype).
- Filtering DNS (e.g. Quad9) configured system-wide; browser DoH disabled.

### 6.4 Remote administration
- Raspberry Pi Connect, linked to the administrator's Raspberry Pi ID. Outbound only, no port forwarding, no pairing code for a scammer to extract.
- Pi Connect runs as the user who enables it, so a shell as `grandma` has no sudo. Plan: a separate `admin` account for shell/escalation, with `grandma` retained for screen sharing. **To be verified on a test device** before committing; fallback is key-only Tailscale SSH.
- Screen sharing requires an active session, hence auto-login + linger.

### 6.5 Downloads: scan every one (the "airlock")
1. Firefox saves to a quarantine folder `grandma` cannot open.
2. A watcher (inotify) runs `clamdscan` and a file-type check on each file.
3. Clean + allowed type: moved to `Documents/Downloads`, friendly notice "Checked and safe".
4. Infected or disallowed type: deleted, admin alerted, friendly notice to her.
5. Allowed types: PDF, DOC/DOCX/ODT, JPG/PNG, TXT. Blocked: executables, scripts, installers, un-inspectable archives.
6. Limitation (documented): ClamAV catches known malware only; it does not detect scam documents. File-type limits and the allow-list carry that risk.

### 6.6 Printing
- CUPS, admin-managed only. `grandma` cannot add/remove printers.
- Printer is **USB, make/model unknown (TBD)**. Setup order: (1) driverless via `ipp-usb`; (2) open-source driver (`hplip`, `epson-inkjet-printer-escpr`, `gutenprint`); (3) proprietary driver if ARM-compatible; (4) fallback: replace with a driverless IPP Wi-Fi printer (~$80–120).
- Printer fault states mapped to plain-language messages on the Home screen ("The printer needs paper or ink. Ask [ADMIN_NAME].").

### 6.7 Backup and recovery
- `rclone` nightly sync of Documents to a dedicated Google Drive folder, using rclone `crypt`.
- Golden image of the configured device plus a spare pre-flashed boot device.
- Provisioning is scripted (shell script or Ansible, kept in a private repo; secrets excluded) so the device can be rebuilt.
- Optional later: read-only root filesystem with persistent data partition.

### 6.8 Updates and monitoring
- Unattended security upgrades for OS and browser, nightly reboot window.
- Device pings a health-check service (e.g. healthchecks.io); admin is alerted if it goes quiet or upgrades fail.

## 7. UX Design

Goal: easy and pleasant. Calm, warm, high-contrast, large text, plain words.

- **Home screen:** a custom full-screen launcher with 4-5 large tiles: Email, Facebook, Write a Letter, My Documents, Help.
- **One thing at a time:** apps open maximized; a permanent bottom bar shows Home, Print, Volume, Help. No window or tab management.
- **Help:** shows [ADMIN_NAME] and [ADMIN_PHONE], and whether remote support is connected.
- **Friendly failures:** blocked sites, scan results and errors use plain-language pages/notifications.
- **Comfort:** large cursor, large default fonts, no lock screen, a clear "Turn off" button.
- **Physical card** by the monitor: "No one from Microsoft, Apple or your bank will ever call. Hang up and call [ADMIN_NAME]. If anything looks wrong, switch it off."
- Custom code is limited to the Home screen and airlock watcher; everything else is configuration.

## 8. Open-Source Components

| Need | Component |
|---|---|
| Download scanning | Cisco-Talos/clamav |
| Backup | rclone/rclone |
| Kiosk autostart reference | geerlingguy/pi-kiosk |
| Browser hardening reference | arkenfox/user.js (selective) |
| Browser policies | Mozilla policy-templates |
| Printing | CUPS, ipp-usb |
| Provisioning | shell script or Ansible |

## 9. Acceptance Tests (before handover)
- Cannot install a package, open a terminal, or reach settings.
- Non-allow-listed site shows the friendly block page.
- Fullscreen fake-alert page is blocked.
- Macro document does not run macros.
- USB storage stick does not mount; printer works.
- EICAR test file is caught by the airlock; a clean PDF is delivered.
- Reboot, then confirm remote screen/shell access.
- Restore Documents from Google Drive; rebuild from spare image.
- 30-minute usability session with the user; adjust layout and wording.

## 10. Open Items / Placeholders
- Printer make/model (USB) - determines driver path.
- [ADMIN_NAME] and [ADMIN_PHONE] for Help page and card.
- User's vision/hearing/dexterity needs (font size, mouse vs touch, monitor size).
- Pi 4 vs 5 and SSD vs MicroSD hardware choice.
- Exact outbound firewall rules and Facebook/Gmail domain list (derive in prototype).
- Verify Pi Connect admin-escalation approach on a test device.
