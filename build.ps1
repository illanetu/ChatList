# Скрипт для создания исполняемого файла ChatList
Set-Location $PSScriptRoot
$version = (python -c "import version; print(version.__version__)").Trim()
$exeName = "ChatList-$version"

Write-Host "Version: $version" -ForegroundColor Cyan
Write-Host "Installing dependencies..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Building exe..." -ForegroundColor Green
if (Test-Path dist) {
    Get-ChildItem dist -Filter "*.exe" | Remove-Item -Force
}
pyinstaller --onefile --windowed --name $exeName --icon app.ico --add-data "logs;logs" main.py

$exePath = Join-Path dist ($exeName + ".exe")
Write-Host ""
Write-Host ("Done: " + $exePath) -ForegroundColor Green
