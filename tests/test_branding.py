"""Branding configuration, brand assets and the 'no DPort in the UI' rule."""
import json
import os
import struct
import tempfile
import unittest

import fakes  # noqa: F401
from fakes import inherited_copyright_holder

HOLDER = inherited_copyright_holder()

from services.branding import load_branding
from services.i18n import LANGUAGES, load_locale

APP = fakes.APP


class BrandingConfig(unittest.TestCase):
    def test_shipped_branding(self):
        b = load_branding()
        self.assertEqual(b.creator_name, "Lucas (KJ)")
        self.assertEqual(b.creator_short_name, "Lucas")
        self.assertEqual([(l.id, l.label, l.url) for l in b.links], [
            ("instagram", "@k_77.0", "https://www.instagram.com/k_77.0/"),
            ("github", "LUCASS7001", "https://github.com/LUCASS7001"),
        ])
        self.assertEqual(b.discord_username, "@l_4")

    def test_discord_username_must_be_plain_text(self):
        for bad in ("https://discord.gg/x", "discord.com/users/1", "a b", "", "x" * 41):
            b = self._load({"creator": {"discord": bad}})
            self.assertEqual(b.discord_username, "", bad)

    def _load(self, data):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(data if isinstance(data, str) else json.dumps(data))
            return load_branding(path)
        finally:
            os.remove(path)

    def test_unsafe_or_unknown_links_are_dropped(self):
        b = self._load({"creator": {"name": "X"}, "links": [
            {"id": "github", "label": "a", "url": "http://github.com/a"},
            {"id": "github", "label": "b", "url": "file:///C:/Windows/notepad.exe"},
            {"id": "github", "label": "c", "url": "javascript:alert(1)"},
            {"id": "tiktok", "label": "d", "url": "https://tiktok.com/@d"},
            {"id": "instagram", "label": "ok", "url": "https://instagram.com/ok"},
        ]})
        self.assertEqual([l.label for l in b.links], ["ok"])
        self.assertEqual(b.creator_name, "X")

    def test_broken_file_falls_back_to_defaults(self):
        b = self._load("{not json")
        self.assertEqual(b.creator_name, "Lucas (KJ)")
        self.assertEqual(b.links, [])


class NoOriginalDeveloperInUi(unittest.TestCase):
    def test_locales_do_not_mention_dport(self):
        for code in LANGUAGES:
            text = " ".join(load_locale(code).values())
            self.assertNotIn("DPort", text, code)
            if HOLDER:
                self.assertNotIn(HOLDER, text, code)

    def test_ui_sources_do_not_mention_dport(self):
        for name in os.listdir(os.path.join(APP, "ui")):
            if name.endswith((".py", ".qss")):
                with open(os.path.join(APP, "ui", name), encoding="utf-8") as f:
                    src = f.read()
                if HOLDER:
                    self.assertNotIn(HOLDER, src, name)
                self.assertNotIn("ORIGINAL_", src, name)

    def test_legal_documents_identify_owner_and_third_party_terms(self):
        """Owner's notice is present; LICENSE defers third-party and inherited
        code to NOTICE.md and licenses/ (wording chosen by the owner)."""
        root = os.path.dirname(APP)
        texts = {}
        for doc in ("NOTICE.md", "LICENSE"):
            with open(os.path.join(root, doc), encoding="utf-8") as f:
                texts[doc] = f.read()
            self.assertIn("Copyright (c) 2026 Lucas", texts[doc], doc)
        self.assertIn("NOTICE.md", texts["LICENSE"])
        self.assertIn("inherited code", texts["LICENSE"].lower())
        self.assertIn("## Third-party components", texts["NOTICE.md"])


ROOT = os.path.dirname(APP)
# Public-facing, non-legal files: no previous publisher identity allowed.
PUBLIC_FILES = [
    "README.md", "CHANGELOG.md", "SECURITY.md", "CONTRIBUTING.md",
    ".github/pull_request_template.md", ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml", ".github/workflows/tests.yml",
    ".github/workflows/release.yml", "packaging/KJDes.spec", "packaging/KJDes.iss",
    "app/branding.json", "app/core/app_info.py", "scripts/build.ps1", "scripts/run_dev.bat",
]


class PublicationHygiene(unittest.TestCase):
    def _read(self, rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()

    def test_public_files_do_not_expose_previous_publisher(self):
        for rel in PUBLIC_FILES:
            text = self._read(rel).lower()
            for needle in [n for n in (HOLDER.lower(), "gmail.com") if n]:
                self.assertNotIn(needle, text, f"{rel}: {needle}")

    def test_private_business_terms_are_not_public(self):
        """Phrases from the private record (only present on the owner's
        machine, git-ignored) must not appear in any public file."""
        import re
        private = os.path.join(ROOT, "legal", "PERMISSION_RECORD.private.md")
        if not os.path.exists(private):
            self.skipTest("private record not present (expected in public checkouts)")
        with open(private, encoding="utf-8") as f:
            needles = {m.group(0).lower() for m in re.finditer(r"\d+\s?%", f.read())}
        self.assertTrue(needles, "could not read the private terms")
        for rel in PUBLIC_FILES + ["LICENSE", "NOTICE.md"]:
            text = self._read(rel).lower()
            for needle in needles:
                self.assertNotIn(needle, text, f"{rel}: {needle}")

    def test_private_records_are_git_ignored(self):
        import subprocess
        r = subprocess.run(["git", "check-ignore", "-q", "legal/PERMISSION_RECORD.private.md"],
                           cwd=ROOT, capture_output=True)
        if r.returncode == 128:
            self.skipTest("not a git checkout")
        self.assertEqual(r.returncode, 0, "legal/ must be ignored by git")

    def test_executable_and_installer_metadata_identify_lucas(self):
        from core import app_info
        self.assertEqual(app_info.APP_NAME, "KJ Des")
        self.assertEqual(app_info.APP_PUBLISHER, "Lucas")
        self.assertEqual(app_info.APP_DESCRIPTION,
                         "A Windows desktop connectivity utility for Discord.")
        spec = self._read("packaging/KJDes.spec")
        self.assertIn("StringStruct('CompanyName', 'Lucas')", spec)
        self.assertIn("StringStruct('ProductName', 'KJ Des')", spec)
        self.assertIn("Copyright (c) 2026 Lucas", spec)
        iss = self._read("packaging/KJDes.iss")
        self.assertIn('#define MyAppPublisher "Lucas"', iss)
        self.assertIn('#define MyAppName "KJ Des"', iss)
        self.assertIn('#define MyAppURL "https://github.com/LUCASS7001"', iss)


class BrandAssets(unittest.TestCase):
    def test_ico_contains_all_windows_sizes(self):
        with open(os.path.join(APP, "assets", "icon.ico"), "rb") as f:
            data = f.read()
        reserved, kind, count = struct.unpack_from("<HHH", data)
        self.assertEqual((reserved, kind), (0, 1))
        sizes = set()
        for i in range(count):
            w, h = struct.unpack_from("<BB", data, 6 + 16 * i)
            sizes.add(w or 256)
        self.assertTrue({16, 24, 32, 48, 256} <= sizes, sizes)

    def test_brand_pngs_exist(self):
        for name in ("icon.png", os.path.join("brand", "kjdes-icon-512.png"),
                     os.path.join("brand", "kjdes-icon-1024.png"),
                     os.path.join("brand", "kjdes-mark-512.png")):
            path = os.path.join(APP, "assets", name)
            self.assertTrue(os.path.getsize(path) > 1000, name)


if __name__ == "__main__":
    unittest.main()
