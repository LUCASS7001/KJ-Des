# Changelog

All notable changes to KJ Des are documented here.

## Unreleased

### Added
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
