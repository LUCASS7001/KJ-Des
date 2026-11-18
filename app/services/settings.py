"""
services/settings.py
Validated user settings (stored in %APPDATA%\\KJ Des\\config.json).

Values are validated on read: an unknown language or a wrong type falls back
to the default instead of propagating. Network recovery data is NEVER stored
here (that file is user-writable); see core/secure_store.py.
"""
from core.config_manager import ConfigManager
from services.i18n import DEFAULT_LANGUAGE, LANGUAGES

SCHEMA = {
    "language": (str, DEFAULT_LANGUAGE),
    "close_to_tray": (bool, True),
    "start_with_windows": (bool, False),
    "log_enabled": (bool, True),
    "tray_hint_shown": (bool, False),
}


class Settings:
    def __init__(self, path: str):
        self._cfg = ConfigManager(path)

    def get(self, key: str):
        kind, default = SCHEMA[key]
        value = self._cfg.get(key, default)
        if type(value) is not kind:
            return default
        if key == "language" and value not in LANGUAGES:
            return default
        return value

    def set(self, key: str, value) -> None:
        kind, _default = SCHEMA[key]
        if type(value) is not kind:
            raise TypeError(f"{key} must be {kind.__name__}")
        if key == "language" and value not in LANGUAGES:
            raise ValueError("unsupported language")
        self._cfg.set(key, value)
