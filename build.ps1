# Скрипт для создания исполняемого файла ChatList
Write-Host "Установка зависимостей..." -ForegroundColor Green
pip install -r requirements.txt

Write-Host ""
Write-Host "Создание исполняемого файла..." -ForegroundColor Green
pyinstaller --onefile --windowed --name "ChatList" --add-data "logs;logs" main.py

Write-Host ""
Write-Host "Готово! Исполняемый файл: dist\ChatList.exe" -ForegroundColor Green
