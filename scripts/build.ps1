<#
  KJ Des — Windows release build.

  1. Runs the test suite (offscreen Qt; no network settings are touched).
  2. Regenerates app/assets/icon.ico from the vector logo.
  3. Builds dist\KJDes\KJDes.exe with PyInstaller (windowed, UAC manifest).
  4. Runs the frozen self-test (loads every bundled resource, renders the UI).
  5. If Inno Setup 6 is installed, compiles installer\KJDes-Setup-<version>.exe.

  Usage (from the repository root):
      powershell -ExecutionPolicy Bypass -File scripts\build.ps1
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Host '[*] Creating virtual environment (.venv)'
    python -m venv .venv
    & $python -m pip install --upgrade pip
}
& $python -m pip install -r requirements-dev.txt
if ($LASTEXITCODE) { throw 'dependency installation failed' }

Write-Host '[1/5] Tests'
$env:QT_QPA_PLATFORM = 'offscreen'
& $python -m pytest -q
if ($LASTEXITCODE) { throw 'tests failed' }
Remove-Item Env:\QT_QPA_PLATFORM

Write-Host '[2/5] Icon'
& $python packaging\make_icon.py
if ($LASTEXITCODE) { throw 'icon generation failed' }

Write-Host '[3/5] PyInstaller'
& $python -m PyInstaller --noconfirm --clean --distpath dist --workpath build packaging\KJDes.spec
if ($LASTEXITCODE) { throw 'PyInstaller failed' }

Write-Host '[4/5] Frozen self-test (a UAC prompt appears because KJDes.exe requires administrator)'
$shot = Join-Path $root 'build\self-test.png'
$p = Start-Process -FilePath 'dist\KJDes\KJDes.exe' -ArgumentList '--self-test', "`"$shot`"" -Wait -PassThru
if ($p.ExitCode -ne 0) { throw "self-test failed with exit code $($p.ExitCode)" }

Write-Host '[5/5] Installer'
$iscc = @(
    $env:KJDES_ISCC,
    (Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'),
    (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe')
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if ($iscc) {
    & $iscc packaging\KJDes.iss
    if ($LASTEXITCODE) { throw 'Inno Setup compile failed' }
    Get-ChildItem installer\KJDes-Setup-*.exe | ForEach-Object {
        $hash = (Get-FileHash $_.FullName -Algorithm SHA256).Hash
        "$hash  $($_.Name)" | Out-File -Encoding ascii "$($_.FullName).sha256"
        Write-Host "    $($_.Name)  SHA256=$hash"
    }
} else {
    Write-Warning 'Inno Setup 6 not found: installer skipped (dist\KJDes is the portable build).'
}
Write-Host 'Done.'
