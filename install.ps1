# Build ChatList exe + Inno Setup installer
# Requires: Python, PyInstaller, Inno Setup 6 (iscc in PATH or default install)

Set-Location $PSScriptRoot

$version = (python -c "import version; print(version.__version__)").Trim()
$exeName = "ChatList-$version"
$exePath = Join-Path dist ($exeName + ".exe")

Write-Host "ChatList $version - build and installer" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $exePath)) {
    Write-Host "Running build.ps1..." -ForegroundColor Yellow
    & (Join-Path $PSScriptRoot build.ps1)
    if (-not (Test-Path $exePath)) {
        Write-Host "Error: $exePath not found" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Found exe: $exePath" -ForegroundColor Green
}

$isccExe = $null
if ($env:ISCC_PATH -and (Test-Path $env:ISCC_PATH)) { $isccExe = $env:ISCC_PATH }
if (-not $isccExe) {
    $iscc = Get-Command iscc -ErrorAction SilentlyContinue
    if ($iscc) { $isccExe = $iscc.Source }
}
$paths = @(
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
)
foreach ($p in $paths) {
    if (-not $isccExe -and $p -and (Test-Path $p)) { $isccExe = $p; break }
}
if (-not $isccExe) {
    Write-Host "Error: Inno Setup 6 not found. Install from https://jrsoftware.org/isdl.php or set ISCC_PATH to ISCC.exe path." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Building installer..." -ForegroundColor Green
& $isccExe /DMyAppVersion=$version install.iss

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host ("Done: install\ChatList-$version-setup.exe") -ForegroundColor Green
} else {
    Write-Host ("Installer build failed, exit code " + $LASTEXITCODE) -ForegroundColor Red
    exit 1
}
