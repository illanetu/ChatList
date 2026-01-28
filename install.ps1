# Сборка ChatList и создание инсталлятора Inno Setup
# Требуется: Python, PyInstaller, Inno Setup 6 (iscc в PATH)

Set-Location $PSScriptRoot

$version = (python -c "import version; print(version.__version__)").Trim()
$exeName = "ChatList-$version"
$exePath = "dist\$exeName.exe"

Write-Host "ChatList $version — сборка и инсталлятор" -ForegroundColor Cyan
Write-Host ""

# 1. Сборка exe
if (-not (Test-Path $exePath)) {
    Write-Host "Запуск build.ps1..." -ForegroundColor Yellow
    & "$PSScriptRoot\build.ps1"
    if (-not (Test-Path $exePath)) {
        Write-Host "Ошибка: не найден $exePath" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "Найден exe: $exePath" -ForegroundColor Green
}

# 2. Inno Setup
$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if (-not $iscc) {
    $isccPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (Test-Path $isccPath) {
        $iscc = $isccPath
    } else {
        Write-Host "Ошибка: Inno Setup 6 не найден. Установите и добавьте iscc в PATH или укажите путь к ISCC.exe." -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "Создание инсталлятора..." -ForegroundColor Green
& $iscc /DMyAppVersion=$version "install.iss"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "Готово! Инсталлятор: installer\ChatList-$version-setup.exe" -ForegroundColor Green
} else {
    Write-Host "Ошибка сборки инсталлятора (код $LASTEXITCODE)" -ForegroundColor Red
    exit 1
}
