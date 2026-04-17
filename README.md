# translatePSD

Инструмент для локализации проектной документации с китайского на русский:
- Streamlit UI для Excel, PDF и DXF
- пакетная обработка папок
- DXF-перевод с OCR fallback
- базовая нормализация и валидация результата

## Что исправлено

- убран секрет из исходников, конфиг читается из переменных окружения
- добавлен недостающий модуль `bbox_to_dxf.py`
- исправлена DXF-запись и выбор результирующего текста
- `translate_pdf` теперь создаёт выходной PDF-файл-копию и sidecar с переводом
- убраны жёсткие абсолютные пути из `run_*.py`
- добавлены зависимости и базовая документация

## Установка

Проект лучше держать в пути без кириллицы, иначе на Windows виртуальные окружения и часть инструментов могут ломаться.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Переменные окружения

Скопируйте `.env.example` в `.env` или задайте переменные вручную:

- `DEEPSEEK_API_KEY`
- `DEEPSEEK_BASE_URL`
- `OLLAMA_URL`
- `OLLAMA_MODEL`

## Запуск

### Streamlit

```powershell
streamlit run app.py
```

### DXF

```powershell
python run_dxf.py input.dxf output.dxf
```

### DXF + OCR

```powershell
python run_full.py input.dxf output.dxf --tmp-dir tmp
```

### Пакетная обработка

```python
from translate_project import translate_project

translate_project("source_dir", "output_dir")
```

## Ограничения

- Для PDF сейчас сохраняется исходный PDF и отдельный `*.translated.txt` с переводом текста.
- Для OCR нужны установленные зависимости `paddleocr` и `opencv-python`.
- Без работающего Ollama переводчик вернёт исходный текст как fallback.
