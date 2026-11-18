# Notices

KJ Des — Copyright (c) 2026 Lucas. See `LICENSE` for the terms that apply to
the KJ Des contributions. The components below keep their own copyright and
license terms.


| KJ Des file | Relationship to the inherited code |
|---|---|
| `app/core/discord_unblock.py` | Relay (TLS ClientHello record fragmentation, SNI allow-list, DoH resolution, TLS race) and hosts handling; KJ Des markers, comments and a read-only `routed_hosts()` helper changed/added. |
| `app/core/dns_manager.py`, `app/core/adapter_manager.py` | Inherited, unchanged code. |
| `app/core/failsafe.py`, `app/core/secure_store.py` | Inherited; KJ Des task name, folder names and comments. |
| `app/core/log_manager.py`, `config_manager.py`, `paths.py`, `startup_manager.py` | Inherited; KJ Des names and defaults. |
| `app/core/connection.py`, `app/core/recovery.py` | Connect / restore / watchdog / start-up recovery sequence moved out of the inherited GUI into new UI-independent classes; end-to-end verification and port pre-check added by KJ Des. |
| `app/security/elevation.py`, `app/security/single_instance.py` | Inherited elevation and single-instance logic with KJ Des identifiers. |
| `packaging/KJDes.iss` | Inherited installer safety logic (verified install target, safe uninstall); KJ Des identity, localization and isolation fixes. |
| `tests/test_*.py` (engine, failsafe and installer tests) | Inherited test suite, adapted. |

All other files were written for KJ Des.

## Third-party components

| Component | Use | License | Text |
|---|---|---|---|
| **Qt 6 / PySide6 6.12 (Essentials) and Shiboken6** — The Qt Company | GUI toolkit | LGPL-3.0-only (or GPL-2.0/GPL-3.0, or commercial) | https://www.gnu.org/licenses/lgpl-3.0.txt |
| **CPython 3.14** — Python Software Foundation | Runtime embedded by PyInstaller | PSF License Agreement | `licenses/Python-PSF-LICENSE.txt` |
| **OpenSSL 3** (part of the CPython distribution) | TLS for DoH and verification | Apache-2.0 | https://www.openssl.org/source/license.html |
| **Inter** typeface — The Inter Project Authors | UI font (Latin) | SIL Open Font License 1.1 | `licenses/Inter-OFL-1.1.txt` |
| **PyInstaller** bootloader | Executable packaging | GPL-2.0 with bootloader exception | https://pyinstaller.org/en/stable/license.html |
| **Inno Setup** | Installer | Inno Setup License | https://jrsoftware.org/files/is/license.txt |

### LGPL (Qt / PySide6) compliance notes

- KJ Des is distributed as a **one-folder** build: the Qt and PySide6 DLLs /
  `.pyd` modules are separate files in `_internal\PySide6\`, so users can
  replace them with their own builds, as the LGPL requires.
- Qt and PySide6 were not modified.
- Before public binary distribution, place the full LGPL-3.0 and GPL-3.0 texts
  in `licenses/` (they are not shipped inside the PySide6 wheel) and keep a link
  to the Qt/PySide6 source (https://download.qt.io/official_releases/QtForPython/).

## Artwork

`app/assets/artwork.png` was supplied by the KJ Des owner as the official
artwork. Its origin and usage rights should be confirmed before public
distribution (see "Publication checklist" in `README.md`).

## Trademarks

Discord is a trademark of Discord Inc. KJ Des is not affiliated with or
endorsed by Discord Inc.; the name is used only to describe compatibility.
The status glyph in the UI is an original drawing, not the Discord logo file.
