"""
Upgrade over an installation that left only its DNS backup behind
(1.0.1 user stuck by GitHub issue #1: uninstall AND update were both refused).

1) Native: the real "UPGRADE DECISION" block from packaging/KJDes.iss is
   compiled into a throw-away probe setup and its decision table is checked.
2) Source rules: setup never deletes/changes the backup, never closes or kills
   KJ Des when a backup is pending, and the uninstaller stays blocked.
"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT = (ROOT / "packaging/KJDes.iss").read_text(encoding="utf-8")
BEGIN = "{ ===== KJDES UPGRADE DECISION BEGIN ===== }"
END = "{ ===== KJDES UPGRADE DECISION END ===== }"
BLOCK = TEXT.split(BEGIN, 1)[1].split(END, 1)[0]
PREPARE = TEXT.split("function PrepareToInstall(var NeedsRestart: Boolean): string;", 1)[1] \
    .split("procedure CurStepChanged", 1)[0]

PROCEED, KEEP, ACTIVE, RUNNING = 0, 1, 2, 3
# (backup present, hosts residue, running known, running) -> decision
TABLE = {
    "clean_system": ((False, False, True, False), PROCEED),
    "stuck_101_user": ((True, False, True, False), KEEP),
    "backup_app_running": ((True, False, True, True), RUNNING),
    "backup_running_unknown": ((True, False, False, True), RUNNING),
    "connected": ((True, True, True, True), ACTIVE),
    "hosts_left_no_backup": ((False, True, True, False), ACTIVE),
    "hosts_left_with_backup_idle": ((True, True, True, False), ACTIVE),
}

PROBE = r"""
[Setup]
AppName=KJ Des upgrade decision test
AppVersion=1
DefaultDirName={tmp}\NeverInstalled
PrivilegesRequired=lowest
Uninstallable=no
OutputBaseFilename=probe
[Code]
%(block)s

var Report: string;

procedure Check(const Name: string; B, H, K, R: Boolean; Want: Integer);
var Got: Integer;
begin
  Got := UpgradeDecision(B, H, K, R);
  if Got = Want then SaveStringToFile(Report, Name + ': PASS' + #13#10, True)
  else SaveStringToFile(Report, Name + ': got ' + IntToStr(Got) + #13#10, True);
end;

function InitializeSetup(): Boolean;
begin
  Report := ExpandConstant('{param:REPORT}');
%(cases)s
  Result := False;
end;
"""


@unittest.skipUnless(os.name == "nt", "Windows/Inno native test")
class UpgradeDecisionNative(unittest.TestCase):
    def test_decision_table(self):
        compiler = Path(os.environ.get("KJDES_ISCC") or
                        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/Inno Setup 6/ISCC.exe")
        if not compiler.exists():
            self.skipTest("Inno Setup compiler unavailable")
        calls = "\n".join(
            f"  Check('{n}', {', '.join(str(v) for v in args)}, {want});"
            for n, (args, want) in TABLE.items())
        with tempfile.TemporaryDirectory(prefix="kjdes-upgrade-test-") as tmp:
            base = Path(tmp)
            (base / "probe.iss").write_text(PROBE % {"block": BLOCK, "cases": calls}, encoding="utf-8-sig")
            done = subprocess.run([str(compiler), "/Q", "/O" + tmp, str(base / "probe.iss")],
                                  capture_output=True, text=True, timeout=60)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            report = base / "result.txt"
            subprocess.run([str(base / "probe.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                            "/REPORT=" + str(report)], capture_output=True, timeout=60)
            lines = report.read_text(encoding="utf-8-sig").strip().splitlines()
            self.assertEqual(len(lines), len(TABLE), lines)
            for line in lines:
                self.assertTrue(line.endswith(": PASS"), line)


class UpgradeSourceRules(unittest.TestCase):
    def test_block_is_pure(self):
        for forbidden in ("Exec", "DeleteFile", "FileExists", "RegWrite", "Stop-Process"):
            self.assertNotIn(forbidden, BLOCK)

    def test_keep_backup_branch_exits_before_any_close_or_kill(self):
        keep = PREPARE.split("UPGRADE_KEEP_BACKUP: begin", 1)[1].split("end;", 1)[0]
        self.assertIn("exit;", keep)
        self.assertNotIn("StopVerifiedPassiveKJDes", keep)
        self.assertLess(PREPARE.index("UPGRADE_KEEP_BACKUP: begin"),
                        PREPARE.index("StopVerifiedPassiveKJDes"))

    def test_running_check_only_when_backup_and_no_hosts_residue(self):
        self.assertIn("if Backup and not Residue then", PREPARE)
        self.assertIn("Known := False;", PREPARE)
        self.assertIn("Running := True;", PREPARE)      # unknown == running (fail closed)

    def test_running_probe_is_read_only(self):
        probe = TEXT.split("function AnyKJDesRunning", 1)[1].split("function PrepareToInstall", 1)[0]
        self.assertIn("Get-Process -Name KJDes", probe)
        for forbidden in ("Stop-Process", "taskkill", "Kill"):
            self.assertNotIn(forbidden, probe)

    def test_setup_never_touches_the_backup(self):
        code = "\n".join(ln for ln in TEXT.splitlines() if "dns_state.json" in ln)
        self.assertEqual(code.count("dns_state.json"), 1, code)
        self.assertIn("FileExists(ExpandConstant('{commonappdata}\\KJ Des\\dns_state.json'))", code)
        for section in ("[InstallDelete]", "[UninstallDelete]"):
            self.assertNotIn(section, TEXT)

    def test_uninstall_still_blocked_by_backup(self):
        init = TEXT.split("function InitializeUninstall(): Boolean;", 1)[1]
        self.assertIn("Problems := RestoreProblems();", init)
        rp = TEXT.split("function RestoreProblems(): string;", 1)[1].split("end;", 1)[0]
        self.assertIn("if DnsBackupPresent() then", rp)
        self.assertIn("if KJDesHostsResidue() then", rp)

    def test_message_localized(self):
        for lang in ("arabic", "turkish", "english"):
            self.assertIn(f"{lang}.PendingRestoreRunning=", TEXT)


if __name__ == "__main__":
    unittest.main()
