import hashlib
import os
import re
from functools import lru_cache

import pandas as pd


DEFAULT_PATH = os.getenv("NORMATIVE_DICTIONARY_PATH", "dictionary/normative_terms.xlsx")
APPROVED_SEED_PATH = os.getenv("APPROVED_TERMS_SEED_PATH", "dictionary/approved_terms_seed.csv")
CANDIDATES_TEMPLATE_PATH = os.getenv("CANDIDATES_TEMPLATE_PATH", "dictionary/candidates_template.csv")
APPROVED_SHEET = "approved_terms"
CANDIDATES_SHEET = "candidates"
APPROVED_COLUMNS = ["SECTION", "CN", "RU", "STANDARD_REF", "STATUS", "NOTE"]
CANDIDATE_COLUMNS = [
    "SECTION",
    "CN",
    "CURRENT_RU",
    "SOURCE",
    "STANDARD_REF",
    "STATUS",
    "NOTE",
    "COUNT",
    "CONFIDENCE",
    "RECOMMENDED",
    "DOC_KEYS",
]
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
PUNCT_ONLY_RE = re.compile(r"^[\s\d,.;:()/%×\-–—_:+*\\[\]{}<>|]+$")
LATIN_SHORT_RE = re.compile(r"^[A-Za-z]{1,3}$")


def _bootstrap_terms():
    if os.path.exists(APPROVED_SEED_PATH):
        frame = pd.read_csv(APPROVED_SEED_PATH, dtype=str).fillna("")
        for column in APPROVED_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        return frame[APPROVED_COLUMNS].to_dict(orient="records")

    return [
        {"SECTION": "ТХ", "CN": "工业流程说明", "RU": "описание промышленного процесса", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ОВ", "CN": "通风", "RU": "вентиляция", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ОВ", "CN": "排风", "RU": "вытяжная вентиляция", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
        {"SECTION": "ВК", "CN": "排水沟", "RU": "водоотводный лоток", "STANDARD_REF": "Внутренний словарь РК", "STATUS": "APPROVED", "NOTE": ""},
    ]


def _bootstrap_candidates_template():
    if os.path.exists(CANDIDATES_TEMPLATE_PATH):
        frame = pd.read_csv(CANDIDATES_TEMPLATE_PATH, dtype=str).fillna("")
        for column in CANDIDATE_COLUMNS:
            if column not in frame.columns:
                frame[column] = ""
        return frame[CANDIDATE_COLUMNS]

    return pd.DataFrame(columns=CANDIDATE_COLUMNS)


def _ensure_workbook(path=DEFAULT_PATH):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    if os.path.exists(path):
        return path

    approved = pd.DataFrame(_bootstrap_terms(), columns=APPROVED_COLUMNS)
    candidates = _bootstrap_candidates_template()

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        approved.to_excel(writer, sheet_name=APPROVED_SHEET, index=False)
        candidates.to_excel(writer, sheet_name=CANDIDATES_SHEET, index=False)

    return path


def rebuild_normative_dictionary(path=DEFAULT_PATH):
    workbook = _ensure_workbook(path)
    approved = pd.DataFrame(_bootstrap_terms(), columns=APPROVED_COLUMNS)
    candidates = _bootstrap_candidates_template()

    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        approved.to_excel(writer, sheet_name=APPROVED_SHEET, index=False)
        candidates.to_excel(writer, sheet_name=CANDIDATES_SHEET, index=False)

    refresh_normative_dictionary_cache()
    return {
        "workbook": workbook,
        "approved_rows": len(approved),
        "candidate_rows": len(candidates),
    }


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


def _status_is_recommended(value):
    return str(value).strip().upper() in {"RECOMMENDED", "TRUE", "1", "ДА", "YES"}


def _score_candidate(source_text, translated_text, source_name):
    source = str(source_text).strip()
    translated = str(translated_text).strip()
    score = 0.0

    if source and translated:
        score += 0.1
    if translated and not CHINESE_RE.search(translated):
        score += 0.35
    if CYRILLIC_RE.search(translated):
        score += 0.2
    if translated and len(translated) >= max(4, int(len(source) * 0.25)):
        score += 0.15
    if str(source_name).startswith(("memory", "section_dict", "ollama_duplicate", "deepseek_duplicate")):
        score += 0.15
    if str(source_name).startswith("deepseek"):
        score += 0.1
    if translated and translated.lower() != source.lower():
        score += 0.05

    return round(min(score, 1.0), 2)


def _normalized_text(value):
    return re.sub(r"\s+", " ", str(value).strip())


def _looks_like_noise(value):
    text = _normalized_text(value)
    if not text:
        return True
    if PUNCT_ONLY_RE.match(text):
        return True
    if LATIN_SHORT_RE.match(text):
        return True
    if len(text) <= 2:
        return True
    return False


def _is_viable_candidate(section, source_text, translated_text, source_name):
    source = _normalized_text(source_text)
    translated = _normalized_text(translated_text)
    source_name = str(source_name).strip()
    section = str(section).strip() or "UNKNOWN"

    if not source or not translated:
        return False
    if _looks_like_noise(source) or _looks_like_noise(translated):
        return False
    if not CHINESE_RE.search(source):
        return False
    if CHINESE_RE.search(translated):
        return False
    if not CYRILLIC_RE.search(translated):
        return False
    if len(translated) < max(4, int(len(source) * 0.18)):
        return False
    if section == "UNKNOWN" and len(translated) < 8:
        return False
    if source_name.startswith("section_dict") and len(translated) < 8:
        return False
    return True


def _recommend_candidate(count, confidence, translated_text):
    translated = str(translated_text).strip()
    if not translated:
        return False
    if CHINESE_RE.search(translated):
        return False
    return int(count) >= 2 and float(confidence) >= 0.75


def _document_fingerprint(df):
    parts = []
    for _, row in df.iterrows():
        parts.append(
            "||".join(
                [
                    str(row.get("section", row.get("SECTION", "UNKNOWN"))).strip(),
                    str(row.get("text", "")).strip(),
                ]
            )
        )

    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha1(payload).hexdigest()[:12]


def _split_doc_keys(value):
    raw = str(value).strip()
    if not raw:
        return set()
    return {item for item in raw.split("|") if item}


def _join_doc_keys(keys):
    return "|".join(sorted(set(keys)))


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
    document_key = _document_fingerprint(df)

    known = set()
    for frame, translation_column in ((approved, "RU"),):
        for _, row in frame.iterrows():
            known.add((str(row["SECTION"]).strip(), str(row["CN"]).strip(), str(row.get(translation_column, "")).strip()))

    existing = {}
    for idx, row in candidates.iterrows():
        key = (str(row["SECTION"]).strip(), str(row["CN"]).strip(), str(row["CURRENT_RU"]).strip())
        existing[key] = idx

    seen_in_document = set()
    for _, row in df.iterrows():
        source = str(row.get("text", "")).strip()
        if not source:
            continue

        section = str(row.get("section", row.get("SECTION", "UNKNOWN"))).strip() or "UNKNOWN"
        current_ru = str(row.get("normalized", row.get("translated", ""))).strip()
        source_name = str(row.get("translation_source", "document")).strip() or "document"
        if not _is_viable_candidate(section, source, current_ru, source_name):
            continue
        key = (section, source, current_ru)

        if key in known:
            continue
        if key in seen_in_document:
            continue
        seen_in_document.add(key)

        confidence = _score_candidate(source, current_ru, source_name)

        if key in existing:
            idx = existing[key]
            doc_keys = _split_doc_keys(candidates.at[idx, "DOC_KEYS"])
            if document_key not in doc_keys:
                doc_keys.add(document_key)
            count = len(doc_keys)
            candidates.at[idx, "COUNT"] = count
            candidates.at[idx, "SOURCE"] = source_name
            candidates.at[idx, "DOC_KEYS"] = _join_doc_keys(doc_keys)
            candidates.at[idx, "CONFIDENCE"] = max(float(candidates.at[idx, "CONFIDENCE"] or 0), confidence)
            if _status_is_approved(candidates.at[idx, "STATUS"]):
                continue
            if _recommend_candidate(count, candidates.at[idx, "CONFIDENCE"], current_ru):
                candidates.at[idx, "STATUS"] = "RECOMMENDED"
                candidates.at[idx, "RECOMMENDED"] = "YES"
            elif not str(candidates.at[idx, "STATUS"]).strip():
                candidates.at[idx, "STATUS"] = "NEW"
        else:
            count = 1
            recommended = _recommend_candidate(count, confidence, current_ru)
            new_row = {
                "SECTION": section,
                "CN": source,
                "CURRENT_RU": current_ru,
                "SOURCE": source_name,
                "STANDARD_REF": "",
                "STATUS": "RECOMMENDED" if recommended else "NEW",
                "NOTE": "",
                "COUNT": count,
                "CONFIDENCE": confidence,
                "RECOMMENDED": "YES" if recommended else "",
                "DOC_KEYS": document_key,
            }
            candidates = pd.concat([candidates, pd.DataFrame([new_row], columns=CANDIDATE_COLUMNS)], ignore_index=True)
            existing[key] = len(candidates) - 1

    updated = candidates.copy()
    updated = updated.drop_duplicates(subset=["SECTION", "CN", "CURRENT_RU"], keep="last")
    updated = _sanitize_candidates_frame(updated)

    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        approved.to_excel(writer, sheet_name=APPROVED_SHEET, index=False)
        updated.to_excel(writer, sheet_name=CANDIDATES_SHEET, index=False)

    return workbook


def get_recommended_candidates(path=DEFAULT_PATH):
    workbook = _ensure_workbook(path)
    candidates = _read_sheet(workbook, CANDIDATES_SHEET, CANDIDATE_COLUMNS)
    recommended = candidates[
        candidates["STATUS"].apply(_status_is_recommended) | candidates["RECOMMENDED"].apply(_status_is_recommended)
    ].copy()
    if recommended.empty:
        return recommended
    return recommended.sort_values(by=["COUNT", "CONFIDENCE"], ascending=[False, False])


def _sanitize_candidates_frame(candidates):
    sanitized_rows = []

    for _, row in candidates.iterrows():
        section = str(row["SECTION"]).strip() or "UNKNOWN"
        source = _normalized_text(row["CN"])
        translated = _normalized_text(row["CURRENT_RU"])
        source_name = str(row["SOURCE"]).strip() or "document"

        if not _is_viable_candidate(section, source, translated, source_name):
            continue

        confidence = max(float(row.get("CONFIDENCE", 0) or 0), _score_candidate(source, translated, source_name))
        doc_keys = _split_doc_keys(row.get("DOC_KEYS", ""))
        count = max(len(doc_keys), int(float(row.get("COUNT", 0) or 0)))
        recommended = _recommend_candidate(count, confidence, translated)

        sanitized_rows.append(
            {
                "SECTION": section,
                "CN": source,
                "CURRENT_RU": translated,
                "SOURCE": source_name,
                "STANDARD_REF": str(row.get("STANDARD_REF", "")).strip(),
                "STATUS": "RECOMMENDED" if recommended and not _status_is_approved(row.get("STATUS", "")) else str(row.get("STATUS", "")).strip() or ("RECOMMENDED" if recommended else "NEW"),
                "NOTE": str(row.get("NOTE", "")).strip(),
                "COUNT": count,
                "CONFIDENCE": round(min(confidence, 1.0), 2),
                "RECOMMENDED": "YES" if recommended else "",
                "DOC_KEYS": _join_doc_keys(doc_keys),
            }
        )

    if not sanitized_rows:
        return pd.DataFrame(columns=CANDIDATE_COLUMNS)

    sanitized = pd.DataFrame(sanitized_rows, columns=CANDIDATE_COLUMNS)
    sanitized = sanitized.drop_duplicates(subset=["SECTION", "CN", "CURRENT_RU"], keep="last")
    return sanitized


def clean_normative_candidates(path=DEFAULT_PATH):
    workbook = _ensure_workbook(path)
    approved = _read_sheet(workbook, APPROVED_SHEET, APPROVED_COLUMNS)
    candidates = _read_sheet(workbook, CANDIDATES_SHEET, CANDIDATE_COLUMNS)
    cleaned = _sanitize_candidates_frame(candidates)

    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        approved.to_excel(writer, sheet_name=APPROVED_SHEET, index=False)
        cleaned.to_excel(writer, sheet_name=CANDIDATES_SHEET, index=False)

    return len(candidates) - len(cleaned)


def promote_recommended_candidates(path=DEFAULT_PATH):
    workbook = _ensure_workbook(path)
    approved = _read_sheet(workbook, APPROVED_SHEET, APPROVED_COLUMNS)
    candidates = _read_sheet(workbook, CANDIDATES_SHEET, CANDIDATE_COLUMNS)
    recommended = get_recommended_candidates(path)

    if recommended.empty:
        return 0

    approved_rows = approved.copy()
    existing_keys = {
        (str(row["SECTION"]).strip(), str(row["CN"]).strip(), str(row["RU"]).strip())
        for _, row in approved_rows.iterrows()
    }

    promoted = 0
    for _, row in recommended.iterrows():
        key = (str(row["SECTION"]).strip(), str(row["CN"]).strip(), str(row["CURRENT_RU"]).strip())
        if key not in existing_keys:
            approved_rows = pd.concat(
                [
                    approved_rows,
                    pd.DataFrame(
                        [
                            {
                                "SECTION": row["SECTION"],
                                "CN": row["CN"],
                                "RU": row["CURRENT_RU"],
                                "STANDARD_REF": row["STANDARD_REF"],
                                "STATUS": "APPROVED",
                                "NOTE": row["NOTE"],
                            }
                        ],
                        columns=APPROVED_COLUMNS,
                    ),
                ],
                ignore_index=True,
            )
            existing_keys.add(key)
            promoted += 1

        mask = (
            (candidates["SECTION"].astype(str) == str(row["SECTION"]))
            & (candidates["CN"].astype(str) == str(row["CN"]))
            & (candidates["CURRENT_RU"].astype(str) == str(row["CURRENT_RU"]))
        )
        candidates.loc[mask, "STATUS"] = "APPROVED"
        candidates.loc[mask, "RECOMMENDED"] = ""

    approved_rows = approved_rows.drop_duplicates(subset=["SECTION", "CN", "RU"], keep="last")

    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        approved_rows.to_excel(writer, sheet_name=APPROVED_SHEET, index=False)
        candidates.to_excel(writer, sheet_name=CANDIDATES_SHEET, index=False)

    refresh_normative_dictionary_cache()
    return promoted
