from __future__ import annotations

import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

import pandas as pd

from normative_dictionary import load_normative_dictionary
from translator_deepseek import deepseek_available, deepseek_chat


BOOSTER_TERMS_PATH = os.getenv("BOOSTER_TERMS_PATH", "dictionary/deepseek_terms.json")
CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
CHINESE_FRAGMENT_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\[.*?\])\s*```", flags=re.DOTALL)


def _norm(value):
    return re.sub(r"\s+", " ", str(value or "").strip())


def _ensure_parent(path=BOOSTER_TERMS_PATH):
    parent = Path(path).parent
    if str(parent):
        parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=4)
def load_booster_terms(path=BOOSTER_TERMS_PATH):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_booster_terms(terms, path=BOOSTER_TERMS_PATH):
    _ensure_parent(path)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(terms, file, ensure_ascii=False, indent=2, sort_keys=True)
    load_booster_terms.cache_clear()


def _known_sources():
    known = set()
    for section_terms in load_normative_dictionary().values():
        known.update(str(key).strip() for key in section_terms)
    for section_terms in load_booster_terms().values():
        if isinstance(section_terms, dict):
            known.update(str(key).strip() for key in section_terms)
    return {item for item in known if item}


def _candidate_is_useful(text):
    value = _norm(text)
    if not value:
        return False
    if not CHINESE_RE.search(value):
        return False
    cn_chars = len(CHINESE_RE.findall(value))
    if cn_chars < 2:
        return False
    if len(value) > 80:
        return False
    return True


def extract_booster_candidates(df, *, limit=120):
    if df is None or df.empty or "text" not in df.columns:
        return pd.DataFrame(columns=["section", "cn", "count"])

    known = _known_sources()
    counter = Counter()
    section_by_cn = {}

    for _, row in df.iterrows():
        section = _norm(row.get("section", "UNKNOWN")) or "UNKNOWN"
        text = _norm(row.get("text", ""))
        if not _candidate_is_useful(text):
            continue

        cn_chars = len(CHINESE_RE.findall(text))
        if cn_chars <= 16 and text not in known:
            counter[text] += 2
            section_by_cn.setdefault(text, section)

        for fragment in CHINESE_FRAGMENT_RE.findall(text):
            fragment = _norm(fragment)
            if fragment in known or not _candidate_is_useful(fragment):
                continue
            counter[fragment] += 1
            section_by_cn.setdefault(fragment, section)

    rows = [
        {"section": section_by_cn.get(cn, "UNKNOWN"), "cn": cn, "count": count}
        for cn, count in counter.most_common(limit)
    ]
    return pd.DataFrame(rows, columns=["section", "cn", "count"])


def _parse_deepseek_terms(raw_response):
    raw = str(raw_response or "").strip()
    if not raw:
        return []

    fenced = JSON_BLOCK_RE.search(raw)
    if fenced:
        raw = fenced.group(1)

    try:
        payload = json.loads(raw)
    except Exception:
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            return []
        try:
            payload = json.loads(raw[start : end + 1])
        except Exception:
            return []

    if not isinstance(payload, list):
        return []

    terms = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        section = _norm(item.get("section", "UNKNOWN")) or "UNKNOWN"
        cn = _norm(item.get("cn", ""))
        ru = _norm(item.get("ru", ""))
        note = _norm(item.get("note", ""))
        if not _candidate_is_useful(cn):
            continue
        if not ru or CHINESE_RE.search(ru) or not CYRILLIC_RE.search(ru):
            continue
        terms.append({"section": section, "cn": cn, "ru": ru, "note": note})
    return terms


def suggest_terms_with_deepseek(candidates_df, *, max_terms=80):
    if not deepseek_available():
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")
    if candidates_df is None or candidates_df.empty:
        return []

    sample = candidates_df.head(max_terms).to_dict(orient="records")
    prompt = (
        "You are building a Chinese-to-Russian engineering dictionary for CAD/DXF drawings "
        "and Kazakhstan construction documentation.\n"
        "Translate only terms/labels. Keep concise Russian engineering wording. "
        "Do not invent details. If a candidate is a number/code/noise, omit it.\n"
        "Return ONLY valid JSON array. Each item: "
        '{"section":"UNKNOWN|АР|КЖ|ОВ|ВК|ЭОМ|ТХ","cn":"...","ru":"...","note":"optional"}.\n\n'
        "Candidates with frequency:\n"
        f"{json.dumps(sample, ensure_ascii=False)}"
    )

    answer = deepseek_chat(
        [
            {
                "role": "system",
                "content": "Return only JSON. You are a precise engineering terminology translator.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=2200,
        timeout=120,
    )
    return _parse_deepseek_terms(answer)


def update_booster_terms(terms, path=BOOSTER_TERMS_PATH):
    store = load_booster_terms(path)
    added = 0
    updated = 0

    for item in terms:
        section = _norm(item.get("section", "UNKNOWN")) or "UNKNOWN"
        cn = _norm(item.get("cn", ""))
        ru = _norm(item.get("ru", ""))
        if not _candidate_is_useful(cn) or not ru or CHINESE_RE.search(ru):
            continue
        store.setdefault(section, {})
        if cn in store[section]:
            if store[section][cn] != ru:
                store[section][cn] = ru
                updated += 1
        else:
            store[section][cn] = ru
            added += 1

    save_booster_terms(store, path)
    return {"added": added, "updated": updated, "path": path, "total_sections": len(store)}


def boost_dictionary_with_deepseek(df, *, candidate_limit=120, deepseek_limit=80):
    candidates = extract_booster_candidates(df, limit=candidate_limit)
    terms = suggest_terms_with_deepseek(candidates, max_terms=deepseek_limit)
    summary = update_booster_terms(terms)
    return {
        "candidates": candidates,
        "terms": pd.DataFrame(terms, columns=["section", "cn", "ru", "note"]),
        "summary": summary,
    }
