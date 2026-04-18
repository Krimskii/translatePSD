Файлы в этой папке — это исходные заготовки словарной подсистемы проекта.

- `approved_terms_seed.csv` — стартовый набор утвержденных терминов для `approved_terms`
- `candidates_template.csv` — пустой шаблон листа `candidates`
- `section_terms_seed.json` — секционные fallback-словари для `ТХ`, `ОВ`, `ВК`, `ЭОМ`, `КЖ`, `АР`
- `translation_memory.json` — локальная память переводов

Рабочий нормативный словарь собирается в `normative_terms.xlsx`.
Его можно пересоздать командой:

```powershell
python rebuild_dictionaries.py
```
