$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Создаю виртуальное окружение .venv..."
    python -m venv .venv
}

Write-Host "Активирую окружение и запускаю приложение..."
& ".\.venv\Scripts\python.exe" -m streamlit run app.py
