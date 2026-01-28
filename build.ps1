# Скрипт для создания исполняемого файла ChatList
Set-Location $PSScriptRoot
$version = (python -c "import version; print(version.__version__)").Trim()
$exeName = "ChatList-$version"

Write-Host "Версия: $version" -ForegroundColor Cyan
Write-Host "Установка зависимостей..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Создание исполняемого файла..." -ForegroundColor Green
pyinstaller --onefile --windowed --name $exeName --icon "app.ico" --add-data "logs;logs" main.py

Write-Host ""
Write-Host "Готово! Исполняемый файл: dist\$exeName.exe" -ForegroundColor Green
