param([string]$FlutterPath)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
if (-not $FlutterPath) {
    $command = Get-Command flutter -ErrorAction SilentlyContinue
    if ($command) { $FlutterPath = $command.Source }
    else { $FlutterPath = Join-Path $project 'build/mobile-tools/flutter/bin/flutter.bat' }
}
if (-not (Test-Path -LiteralPath $FlutterPath)) { throw 'Install Flutter 3.47.9 or pass -FlutterPath.' }
$FlutterPath = (Resolve-Path -LiteralPath $FlutterPath).Path
Push-Location (Join-Path $project 'mobile')
try {
    & $FlutterPath pub get --enforce-lockfile
    if ($LASTEXITCODE -ne 0) { throw 'Locked dependencies failed.' }
    & $FlutterPath analyze
    if ($LASTEXITCODE -ne 0) { throw 'Flutter analysis failed.' }
    & $FlutterPath test
    if ($LASTEXITCODE -ne 0) { throw 'Mobile tests failed.' }
    & $FlutterPath build apk --release
    if ($LASTEXITCODE -ne 0) { throw 'Android APK build failed.' }
} finally { Pop-Location }
& python (Join-Path $project 'scripts/package_mobile.py')
if ($LASTEXITCODE -ne 0) { throw 'Mobile packaging failed.' }
