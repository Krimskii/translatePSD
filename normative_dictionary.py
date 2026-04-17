import os
from functools import lru_cache

import pandas as pd


DEFAULT_PATH = os.getenv("NORMATIVE_DICTIONARY_PATH", "dictionary/normative_terms.xlsx")
APPROVED_SHEET = "approved_terms"
CANDIDATES_SHEET = "candidates"
APPROVED_COLUMNS = ["SECTION", "CN", "RU", "STANDARD_REF", "STATUS", "NOTE"]
CANDIDATE_COLUMNS = ["SECTION", "CN", "CURRENT_RU", "SOURCE", "STANDARD_REF", "STATUS", "NOTE"]


def _bootstrap_terms():
    return [
        {"SECTION": "ОВ", "CN": "通风", "RU": "вентиляция", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ОВ", "CN": "排风", "RU": "вытяжная вентиляция", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ОВ", "CN": "送风", "RU": "приточная вентиляция", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ОВ", "CN": "风管", "RU": "воздуховод", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ВК", "CN": "排水沟", "RU": "водоотводный лоток", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ВК", "CN": "污水沟", "RU": "лоток сточных вод", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ВК", "CN": "方井", "RU": "квадратный смотровой колодец", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ВК", "CN": "圆井", "RU": "круглый смотровой колодец", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "КЖ", "CN": "钢构柱", "RU": "стальная колонна", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "КЖ", "CN": "柱面", "RU": "грань колонны", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "КЖ", "CN": "行车牛腿", "RU": "подкрановая консоль", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "АР", "CN": "车间门", "RU": "дверь цеха", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ЭОМ", "CN": "桥架", "RU": "кабельный лоток", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
    ]


def _ensure_workbook(path=DEFAULT_PATH):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if os.path.exists(path):
        return path

    approved = pd.DataFrame(_bootstrap_terms(), columns=APPROVED_COLUMNS)
    candidates = pd.DataFrame(columns=CANDIDATE_COLUMNS)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        approved.to_excel(writer, sheet_name=APPROVED_SHEET, index=False)
        candidates.to_excel(writer, sheet_name=CANDIDATES_SHEET, index=False)

    return path


def _read_sheet(path, sheet_name, columns):
    try:
        frame = pd.read_excel(path, sheet_name=sheet_name)
    except ValueError:
        frame = pd.DataFrame(columns=columns)

    for column in columns:
        if column not in frame.columns:
            frame[column] = ""

    return frame[columns].fillna("")


def _status_is_approved(value):
    return str(value).strip().upper() in {"APPROVED", "OK", "TRUE", "1", "ДА"}


@lru_cache(maxsize=1)
def load_normative_dictionary(path=DEFAULT_PATH):
    workbook = _ensure_workbook(path)
    approved = _read_sheet(workbook, APPROVED_SHEET, APPROVED_COLUMNS)
    approved = approved[approved["CN"].astype(str).str.strip() != ""]
    approved = approved[approved["RU"].astype(str).str.strip() != ""]
    approved = approved[approved["STATUS"].apply(_status_is_approved)]

    grouped = {}
    for _, row in approved.iterrows():
        section = str(row["SECTION"]).strip() or "ALL"
        grouped.setdefault(section, {})
        grouped[section][str(row["CN"])] = str(row["RU"])

    return grouped


def refresh_normative_dictionary_cache():
    load_normative_dictionary.cache_clear()


def apply_normative_terms(text, section=None):
    value = str(text)
    dictionaries = load_normative_dictionary()

    merged = {}
    for key in ("ALL", str(section or "").strip()):
        for source, target in dictionaries.get(key, {}).items():
            merged[source] = target

    for source, target in sorted(merged.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(source, target)

    return value


def sync_normative_candidates(df, path=DEFAULT_PATH):
    workbook = _ensure_workbook(path)
    approved = _read_sheet(workbook, APPROVED_SHEET, APPROVED_COLUMNS)
    candidates = _read_sheet(workbook, CANDIDATES_SHEET, CANDIDATE_COLUMNS)

    known = set()
    for frame, translation_column in ((approved, "RU"), (candidates, "CURRENT_RU")):
        for _, row in frame.iterrows():
            known.add((str(row["SECTION"]).strip(), str(row["CN"]).strip(), str(row.get(translation_column, "")).strip()))

    rows = []
    for _, row in df.iterrows():
        source = str(row.get("text", "")).strip()
        if not source:
            continue

        section = str(row.get("section", row.get("SECTION", "UNKNOWN"))).strip() or "UNKNOWN"
        current_ru = str(row.get("normalized", row.get("translated", ""))).strip()
        source_name = str(row.get("translation_source", "document")).strip() or "document"
        key = (section, source, current_ru)

        if key in known:
            continue

        rows.append(
            {
                "SECTION": section,
                "CN": source,
                "CURRENT_RU": current_ru,
                "SOURCE": source_name,
                "STANDARD_REF": "",
                "STATUS": "NEW",
                "NOTE": "",
            }
        )
        known.add(key)

    if not rows:
        return workbook

    updated = pd.concat([candidates, pd.DataFrame(rows, columns=CANDIDATE_COLUMNS)], ignore_index=True)
    updated = updated.drop_duplicates(subset=["SECTION", "CN", "CURRENT_RU"], keep="last")

    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        approved.to_excel(writer, sheet_name=APPROVED_SHEET, index=False)
        updated.to_excel(writer, sheet_name=CANDIDATES_SHEET, index=False)

    return workbook
