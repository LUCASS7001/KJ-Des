# Contributing to KJ Des

Thanks for your interest in KJ Des. Bug reports and suggestions are welcome
through the issue tracker.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM = "offscreen"
.venv\Scripts\python -m pytest -q
```

Run the app from source with `scripts\run_dev.bat` (developer mode).

## Ground rules

- **Never run tests against your real network configuration.** All system
  operations go through `app/core/system_ops.py`; tests use `tests/fakes.py`.
- **Do not change the network engine casually.** `app/core/discord_unblock.py`,
  `dns_manager.py`, `failsafe.py`, `secure_store.py`, `connection.py` and
  `recovery.py` are safety-critical. Changes need tests and real-world testing.
- KJ Des may only touch its **own** resources: its marked hosts block, its DNS
  backup, the `KJDesHostsFailsafe` task, its own folders and uninstall entry.
  Never add code that reads or changes another application's resources.
- Do not rename hosts markers, task names, folder names or the installer AppId:
  existing installations depend on them.
- All user-visible text belongs in `app/locales/{ar,tr,en}.json` (all three).
- Keep the UI compact and native (Qt widgets, no web views).
- Do not commit logs, local configuration, certificates, keys or other secrets.

## Pull requests

- One topic per pull request, with a short description and test results.
- Run the full test suite before submitting.
