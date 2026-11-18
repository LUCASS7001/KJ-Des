"""
services/branding.py
Creator name and social links shown in the About dialog, loaded from
app/branding.json (editable without touching code). Localized text such as
the creator's role and the footer lives in app/locales/*.json.

Only https:// links are accepted, so a malformed or tampered file can never
make the About dialog launch a local program or another URL scheme.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import List
from urllib.parse import urlparse

from core.paths import resource_path

KNOWN_LINK_IDS = ("instagram", "github")


@dataclass(frozen=True)
class SocialLink:
    id: str
    label: str
    url: str


@dataclass(frozen=True)
class Branding:
    creator_name: str = "Lucas (KJ)"
    creator_short_name: str = "Lucas"
    discord_username: str = ""          # shown as plain text, never a URL
    links: List[SocialLink] = field(default_factory=list)


def _valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme == "https" and bool(parsed.netloc) and " " not in url


def _valid_handle(value) -> bool:
    """Plain username such as '@l_4': short, no spaces, no URL/scheme."""
    if not isinstance(value, str):
        return False
    v = value.strip()
    return 1 < len(v) <= 40 and " " not in v and "/" not in v and ":" not in v


def load_branding(path: str | None = None) -> Branding:
    path = path or resource_path("branding.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return Branding()
    creator = data.get("creator") if isinstance(data, dict) else None
    creator = creator if isinstance(creator, dict) else {}
    links = []
    for item in (data.get("links") or []) if isinstance(data, dict) else []:
        if not isinstance(item, dict):
            continue
        lid, label, url = item.get("id"), item.get("label"), item.get("url")
        if (lid in KNOWN_LINK_IDS and isinstance(label, str) and label.strip()
                and isinstance(url, str) and _valid_url(url)):
            links.append(SocialLink(lid, label.strip(), url))
    name = creator.get("name")
    short = creator.get("short_name")
    discord = creator.get("discord")
    return Branding(
        discord_username=discord.strip() if _valid_handle(discord) else "",
        creator_name=name.strip() if isinstance(name, str) and name.strip() else Branding.creator_name,
        creator_short_name=short.strip() if isinstance(short, str) and short.strip()
        else Branding.creator_short_name,
        links=links,
    )
