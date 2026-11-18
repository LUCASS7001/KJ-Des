"""
Native Inno Setup test of the installer/uninstaller hosts logic.

The real "HOSTS CLEANER" block is extracted from packaging/KJDes.iss, compiled
into a throw-away setup that only works on temporary files in its own temp
folder (never the system hosts file), and run. Verifies that the uninstaller
treats ONLY KJ Des's marked block as KJ Des's and never touches DPort's block
or unmarked user lines.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "packaging/KJDes.iss").read_text(encoding="utf-8")
BEGIN = "{ ===== KJDES HOSTS CLEANER BEGIN ===== }"
END = "{ ===== KJDES HOSTS CLEANER END ===== }"
BLOCK = TEXT.split(BEGIN, 1)[1].split(END, 1)[0]
KJ_BEGIN = "# >>> KJ Des Discord connectivity >>>"
KJ_END = "# <<< KJ Des Discord connectivity <<<"
DP_BEGIN = "# >>> DPort Discord unblock >>>"
DP_END = "# <<< DPort Discord unblock <<<"
HOSTS = ("updates.discord.com", "discord.com", "gateway.discord.gg",
         "cdn.discordapp.com", "media.discordapp.net")


def _pas(lines):
    """Pascal expression for a CRLF-joined text (trailing CRLF)."""
    return " + ".join("'" + ln.replace("'", "''") + "' + #13#10" for ln in lines) or "''"


USER = ["# user hosts", "127.0.0.1 localhost", "10.0.0.5 nas.local"]
KJ = [KJ_BEGIN] + [f"127.0.0.1 {h}" for h in HOSTS] + [KJ_END]
DP = [DP_BEGIN] + [f"127.0.0.1 {h}" for h in HOSTS] + [DP_END]
BARE = ["127.0.0.1 discord.com"]

CASES = {
    # name: (input lines, expected residue, expected output lines)
    "kj_and_dport": (USER + DP + KJ + BARE, True, USER + DP + BARE),
    "dport_only": (USER + DP + BARE, False, USER + DP + BARE),
    "bare_only": (USER + BARE, False, USER + BARE),
    "kj_missing_end_then_dport": (USER + KJ[:-1] + DP, True, USER + DP),
    "kj_only": (USER + KJ, True, USER),
}

PROBE = r"""
[Setup]
AppName=KJ Des hosts test
AppVersion=1
DefaultDirName={tmp}\NeverInstalled
PrivilegesRequired=lowest
Uninstallable=no
OutputBaseFilename=probe
[Code]
%(block)s

var Report: string;

procedure Note(const S: string);
begin
  SaveStringToFile(Report, S + #13#10, True);
end;

procedure RunCase(const Name, Input: string; WantResidue: Boolean; const Want: string);
var
  P: string; Lines: TArrayOfString; Got: AnsiString; Residue, Cleaned: Boolean;
begin
  P := ExpandConstant('{tmp}\hosts_' + Name);
  SaveStringToFile(P, Input, False);
  LoadStringsFromFile(P, Lines);
  Residue := HostsHasKJDesResidue(Lines);
  Cleaned := CleanHostsBlock(P);
  LoadStringFromFile(P, Got);
  if Residue <> WantResidue then Note(Name + ': residue=' + IntToStr(Integer(Residue)))
  else if not Cleaned then Note(Name + ': clean reported failure')
  else if Got <> Want then Note(Name + ': content differs')
  else Note(Name + ': PASS');
end;

function InitializeSetup(): Boolean;
begin
  Report := ExpandConstant('{param:REPORT}');
%(cases)s
  Result := False;
end;
"""


@unittest.skipUnless(os.name == "nt", "Windows/Inno native test")
class InstallerHostsLogic(unittest.TestCase):
    def test_only_kj_des_block_is_treated_as_kj_des(self):
        compiler = Path(os.environ.get("KJDES_ISCC") or
                        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe")
        if not compiler.exists():
            self.skipTest("Inno Setup compiler unavailable")
        calls = "\n".join(
            f"  RunCase('{name}', {_pas(inp)}, {str(res)}, {_pas(out)});"
            for name, (inp, res, out) in CASES.items())
        code = PROBE % {"block": BLOCK, "cases": calls}
        with tempfile.TemporaryDirectory(prefix="kjdes-hosts-test-") as tmp:
            base = Path(tmp)
            script = base / "probe.iss"
            script.write_text(code, encoding="utf-8-sig")
            compiled = subprocess.run([str(compiler), "/Q", "/O" + tmp, str(script)],
                                      capture_output=True, text=True, timeout=60)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            report = base / "result.txt"
            subprocess.run([str(base / "probe.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                            "/REPORT=" + str(report)], capture_output=True, timeout=60)
            results = report.read_text(encoding="utf-8-sig").strip().splitlines()
            self.assertEqual(len(results), len(CASES), results)
            for line in results:
                self.assertTrue(line.endswith(": PASS"), line)


class InstallerSourceRules(unittest.TestCase):
    def test_no_foreign_identifiers_in_executable_installer_code(self):
        code_lines = [ln for ln in TEXT.splitlines()
                      if not ln.lstrip().startswith((";", "{", "//"))]
        code = "\n".join(code_lines)
        for forbidden in ("7C9E6A54-2D3B-4F81-A6E2-1B0C9D8E7F60",   # DPort AppId
                          "'DPortHostsFailsafe'", "'DiscordConnectHostsFailsafe'",
                          '"DiscordConnectHostsFailsafe"', "{commonappdata}\\DPort",
                          "# >>> DPort"):
            self.assertNotIn(forbidden, code)

    def test_uninstall_messages_are_localized(self):
        for key in ("UninstallNeedsRestore", "ResidueHosts", "ResidueDns",
                    "UninstallCloseFailed", "UninstallHostsFailed", "UninstallUiFailed"):
            for lang in ("arabic", "turkish", "english"):
                self.assertIn(f"{lang}.{key}=", TEXT, f"{lang}.{key}")
        self.assertNotIn("Varsayilana Don islemini tamamlayin", TEXT)

    def test_uninstall_is_blocked_not_forced_while_restore_pending(self):
        init = TEXT.split("function InitializeUninstall(): Boolean;", 1)[1]
        self.assertIn("Problems := RestoreProblems();", init)
        self.assertIn("if Problems <> '' then begin", init)
        step = TEXT.split("procedure CurUninstallStepChanged", 1)[1]
        self.assertIn("if ConnectionRequiresRestore() or not StopVerifiedPassiveKJDes() then", step)
        self.assertNotIn("dns_state.json", step.split("end;\n\n", 1)[0].replace(
            "RestoreProblems", ""), "uninstall must never delete the DNS backup")


if __name__ == "__main__":
    unittest.main()
