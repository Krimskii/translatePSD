$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

Write-Host "Обновляю проект из GitHub..."
git pull

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Создаю виртуальное окружение .venv..."
    python -m venv .venv
}

Write-Host "Обновляю зависимости..."
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Запускаю приложение..."
& ".\.venv\Scripts\python.exe" -m streamlit run app.py
