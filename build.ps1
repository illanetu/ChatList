# Скрипт для создания исполняемого файла
Write-Host "Установка зависимостей..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Создание исполняемого файла..." -ForegroundColor Green
pyinstaller --onefile --windowed --name "MinimalPyQtApp" --icon=NONE main.py

Write-Host ""
Write-Host "Готово! Исполняемый файл: dist\MinimalPyQtApp.exe" -ForegroundColor Green
