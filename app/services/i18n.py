"""
services/i18n.py
JSON-based localization. All user-visible UI text lives in app/locales/*.json.
Missing keys fall back to English, then to the key itself (never crash).
"""
import json
from typing import Callable, Dict, List

from core.paths import resource_path

LANGUAGES = ("ar", "tr", "en")
RTL_LANGUAGES = frozenset({"ar"})
DEFAULT_LANGUAGE = "ar"


def load_locale(code: str) -> Dict[str, str]:
    path = resource_path("locales", f"{code}.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"invalid locale file: {code}")
    return {str(k): str(v) for k, v in data.items()}


class I18n:
    def __init__(self, code: str = DEFAULT_LANGUAGE):
        self._fallback = load_locale("en")
        self._table: Dict[str, str] = {}
        self._listeners: List[Callable[[str], None]] = []
        self.code = ""
        self.set_language(code)

    @property
    def rtl(self) -> bool:
        return self.code in RTL_LANGUAGES

    def set_language(self, code: str) -> None:
        if code not in LANGUAGES:
            code = DEFAULT_LANGUAGE
        if code == self.code:
            return
        self._table = load_locale(code)
        self.code = code
        for listener in list(self._listeners):
            listener(code)

    def on_change(self, listener: Callable[[str], None]) -> None:
        self._listeners.append(listener)

    def t(self, key: str, **kwargs) -> str:
        text = self._table.get(key) or self._fallback.get(key) or key
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError, ValueError):
                pass
        return text

    __call__ = t
