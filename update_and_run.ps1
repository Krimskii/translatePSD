$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

function Get-PythonLauncher {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return "py"
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return "python"
    }

    throw "Не найден Python launcher. Установите Python или добавьте py/python в PATH."
}

Write-Host "Обновляю проект из GitHub..."
git pull

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    Write-Host "Создаю виртуальное окружение .venv..."
    $pythonLauncher = Get-PythonLauncher
    & $pythonLauncher -m venv .venv
}

Write-Host "Обновляю зависимости..."
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

Write-Host "Запускаю приложение..."
& ".\.venv\Scripts\python.exe" -m streamlit run app.py
