# Changelog

All notable changes to KJ Des are documented here.

## 1.0.4 — 2026-11-25

### Fixed
- Updating was impossible for users whose previous version could not finish
  restoring DNS (GitHub issue #1): the old uninstaller refused because the DNS
  backup still existed, and the new installer refused for the same reason.
  Setup now installs over the existing version when only the DNS backup is
  pending, KJ Des' hosts block is absent and no KJ Des process is running.
  Setup never reads, changes or deletes the backup or any DNS setting; the
  updated app resolves the backup at its next start (identity-checked restore,
  otherwise the backup is kept). If KJ Des is still running, setup asks to quit
  it first; an active connection still blocks the update as before. Uninstall
  remains blocked while the backup is unresolved.

## 1.0.3 — 2026-11-25

Version 1.0.2 was not released as an application version (the `v1.0.2` Git tag
points at the 1.0.1 code); this release follows 1.0.1.

### Fixed
- DNS restore no longer gets stuck when Windows recreated an adapter with a new
  InterfaceGuid (e.g. the Hyper-V "Default Switch" at boot) — GitHub issue #1.
  Each saved entry is matched to a current adapter first:
  * saved GUID present -> restore (also when the adapter was renamed);
  * GUID changed but the same real hardware is proven by its burned-in MAC plus
    the saved name or description -> restore, verified against the current GUID;
  * otherwise the decision uses only the saved GUID's own TCP/IP configuration
    (`HKLM\SYSTEM\CurrentControlSet\Services\Tcpip[6]\Parameters\Interfaces\{GUID}`,
    read-only): the entry is cleared without any change when that configuration
    is demonstrably absent, or demonstrably identical to the backup for IPv4 and
    IPv6 (servers in order). Different settings (e.g. KJ Des' Cloudflare values),
    a partial or unreadable configuration -> nothing is changed and the backup is
    kept. A same-named adapter never authorizes clearing; the interface index is
    never used as identity.
- Reconnecting after an interrupted restore could record the DNS KJ Des had
  applied (Cloudflare) as the adapter's "original" when Windows had renamed the
  adapter in between; the following restore then left Cloudflare in place and
  deleted the backup. An adapter whose original is already in the backup (same
  GUID, or proven same hardware) now never gets a second entry. If that cannot
  be decided safely (two entries for one adapter, same hardware not proven, or
  an older entry without GUID while the adapter shows KJ Des' DNS), connecting
  is refused and the backup is kept unchanged. Restore likewise changes nothing
  when several saved entries match the same adapter.
- Restore no longer re-applies settings that are already in place.
- New backups also record the adapter description, burned-in MAC and hardware
  flag. Older backups stay readable and are never reinterpreted.

### Added
- `--diagnose` shows each saved backup entry, which adapter it matches and what a
  restore would do; for a saved GUID that no longer exists it reports that GUID's
  own IPv4/IPv6 configuration (absent / automatic / static(n) / unreadable),
  whether it matches the backup, and whether the result is "clear without
  changes", "retain backup" or "manual recovery required" (read-only).
- `--self-test` also checks that the registry reader works in the packaged build.

## 1.0.1 — 2026-11-18

### Fixed
- Adapters whose name contains characters outside the console code page (for
  example a renamed or localized Ethernet adapter) were listed as `??Ethernet`
  and could not be backed up ("Adapter not uniquely resolved"), so connecting was
  refused. The adapter list is now read as UTF-8 together with each adapter's
  InterfaceGuid and ifIndex. The DNS snapshot and restore resolve the adapter by
  GUID and require the same name, two adapters with the same name are refused
  before anything is read or changed, and the original DNS of every adapter is
  still restored exactly. Nothing is changed unless every adapter is identified
  and backed up.

### Added — diagnostics
- The report lists each adapter's ifIndex and GUID, the SHA-256 of every
  presented certificate, and compares presented CA certificates with known
  genuine fingerprints (report only) to tell a missing root from interception.
- `KJDes.exe --diagnose`: read-only report written to `%APPDATA%\KJ Des\diagnostics.txt`
  (adapters KJ Des would back up and whether each one's DNS can be read; strict TLS
  result for every DoH provider with the presented certificate chain and whether its
  root is in the Windows store; a DoH resolution test). Runs before the single-instance
  check, elevation and the UI: no window, no relay, nothing changed. Exit code 0 = no
  blocking problem, 2 = the app would refuse to connect, 1 = report not produced.
- A failed Windows DNS snapshot now logs its reason (e.g. `DNS family unavailable: ipv4`)
  and the adapter name; the active adapter list and its discovery source are logged.
  Behaviour is unchanged: if any adapter cannot be read, nothing is modified.

## 1.0.0 — 2026-11-18

First KJ Des release, built on an inherited Windows connection engine that is
used with its author's permission (see `NOTICE.md`).

### Added
- Compact frameless PySide6 window (520×560): status ring, live info cards,
  one action button, About / Settings / Activity popups.
- Arabic (default, full RTL), Turkish and English; language switches instantly.
- End-to-end verification: "Connected" requires a certificate-verified TLS
  handshake to `discord.com` through the relay.
- UI-independent connection state machine with watchdog (relay stop or external
  hosts removal → automatic restore).
- System tray with live status, connect/disconnect and an explicit Exit that
  restores settings; manual **Restore defaults** in Settings.
- Packaging: PyInstaller spec with version resource, generated icon, packaged
  `--self-test`, Inno Setup installer (Arabic/Turkish/English), `scripts/build.ps1`.
- Tests for lifecycle, recovery, hosts, localization, settings, single
  instance, elevation, UI and tray.

### Kept from the inherited engine
- TLS ClientHello record-fragmentation relay, SNI allow-list, DoH with
  fallback, TLS race between strategies.
- Exact DNS snapshot/restore, protected recovery store, verified sign-in
  recovery task, hosts handling.

### Changed / removed
- Own hosts markers, scheduled-task name, data folders and IPC identifiers;
  other applications' resources are never touched.
- Removed the inherited Tk GUI, Discord version tile and GitHub updater.

### Added (public snapshot)
- About dialog: KJ Des brand hero, version badge, description, three feature
  cards, creator card (Lucas) with Instagram, GitHub and Discord username,
  footer with a Licenses link. Fully localized (Arabic RTL / Turkish / English).
- Creator name, Discord username and social links configurable in `app/branding.json`.
- New brand mark (angular K, metallic purple gradient, glow); regenerated ICO/PNG
  assets and installer header images.
- Official artwork in the main window and About dialog.
- Connecting checks that `127.0.0.1:443` is free before any DNS or hosts change.
- Repository: README, SECURITY, CONTRIBUTING, issue and pull-request templates,
  release build workflow.

### Fixed
- Installer: uninstall residue checks now consider only KJ Des's own marked
  hosts block and DNS backup; other tools' hosts blocks and unmarked lines are ignored.
- Installer: no longer edits another application's uninstall entry (a wrong
  AppId had been inherited) and no longer deletes another application's
  recovery task name.
- Installer: uninstall warnings are localized and list exactly what is still
  unrestored; nothing is force-deleted.

### Changed
- Publisher and executable/installer metadata now identify Lucas / KJ Des.
- Inherited-code and third-party notices consolidated in `LICENSE` and `NOTICE.md`.
