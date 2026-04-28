from __future__ import annotations

import re
from datetime import datetime

import pandas as pd

from translation_metrics import build_translation_metrics
from translator_deepseek import deepseek_available, deepseek_chat


CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")
NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
MAX_EXAMPLES = 18
MAX_TEXT_LEN = 420


def _clip(value, limit=MAX_TEXT_LEN):
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def _missing_numbers(source_text, translated_text):
    source_numbers = NUMBER_RE.findall(str(source_text or ""))
    if not source_numbers:
        return []
    translated_numbers = set(NUMBER_RE.findall(str(translated_text or "")))
    return [number for number in source_numbers if number not in translated_numbers]


def _row_score(row):
    source_text = str(row.get("text", ""))
    translated_text = str(row.get("translated", row.get("normalized", "")))
    qc_flags = str(row.get("qc_flags", ""))
    score = 0
    if bool(row.get("untranslated_chinese", False)) or CHINESE_RE.search(translated_text):
        score += 100
    if qc_flags:
        score += 60
    if _missing_numbers(source_text, translated_text):
        score += 40
    if str(row.get("translation_source", "")).startswith("fallback"):
        score += 30
    if len(source_text) >= 80 and len(translated_text) < max(8, int(len(source_text) * 0.22)):
        score += 25
    return score


def _build_examples(df, *, max_examples=MAX_EXAMPLES):
    if df is None or df.empty:
        return []

    working = df.copy()
    working["_audit_score"] = working.apply(_row_score, axis=1)
    working = working.sort_values("_audit_score", ascending=False)
    working = working[working["_audit_score"] > 0].head(max_examples)

    examples = []
    for index, row in working.iterrows():
        examples.append(
            {
                "row": int(index) if isinstance(index, int) else str(index),
                "section": str(row.get("section", "UNKNOWN")),
                "source": _clip(row.get("text", "")),
                "translated": _clip(row.get("translated", "")),
                "normalized": _clip(row.get("normalized", "")),
                "translation_source": str(row.get("translation_source", "")),
                "qc_flags": str(row.get("qc_flags", "")),
                "missing_numbers": ", ".join(_missing_numbers(row.get("text", ""), row.get("translated", ""))),
            }
        )

    if examples:
        return examples

    for index, row in df.head(min(max_examples, len(df))).iterrows():
        examples.append(
            {
                "row": int(index) if isinstance(index, int) else str(index),
                "section": str(row.get("section", "UNKNOWN")),
                "source": _clip(row.get("text", "")),
                "translated": _clip(row.get("translated", "")),
                "normalized": _clip(row.get("normalized", "")),
                "translation_source": str(row.get("translation_source", "")),
                "qc_flags": str(row.get("qc_flags", "")),
                "missing_numbers": "",
            }
        )
    return examples


def _format_examples(examples):
    if not examples:
        return "No examples available."

    blocks = []
    for item in examples:
        blocks.append(
            "\n".join(
                [
                    f"Row: {item['row']}",
                    f"Section: {item['section']}",
                    f"Translation source: {item['translation_source']}",
                    f"QC flags: {item['qc_flags'] or '-'}",
                    f"Missing numbers: {item['missing_numbers'] or '-'}",
                    f"CN source: {item['source']}",
                    f"RU translated: {item['translated']}",
                    f"RU normalized: {item['normalized'] or '-'}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)


def build_deepseek_audit_prompt(df, *, file_name="", user_focus=""):
    metrics = build_translation_metrics(df)
    examples = _build_examples(df)
    source_counts = {}
    if df is not None and not df.empty and "translation_source" in df.columns:
        source_counts = df["translation_source"].astype(str).value_counts().head(12).to_dict()

    focus = user_focus.strip() or (
        "Improve translation quality and speed for Chinese CAD/PDF/DOCX/XLSX engineering documentation. "
        "Focus on residual Chinese cleanup, dictionary strategy, OCR/PDF tables, batch routing, and QC."
    )

    return (
        "You are a senior Python engineer, CAD-OCR engineer, and document AI architect.\n"
        "We are building a local Windows Python 3.10 tool for translating Chinese project documentation "
        "for Kazakhstan construction/design workflows.\n\n"
        "Give practical engineering recommendations only. Do not invent facts outside the data. "
        "Prioritize changes that can be implemented in code in this repository.\n\n"
        f"File/context: {file_name or 'current Streamlit dataframe'}\n"
        f"User focus: {focus}\n"
        f"Generated at: {datetime.now().isoformat(timespec='seconds')}\n\n"
        "Current metrics:\n"
        f"{metrics}\n\n"
        "Translation source counts:\n"
        f"{source_counts}\n\n"
        "Problem examples:\n"
        f"{_format_examples(examples)}\n\n"
        "Please return a concise audit in Russian with these sections:\n"
        "1. Главные причины проблем\n"
        "2. Что исправить в пайплайне сейчас\n"
        "3. Что добавить в словари/память\n"
        "4. Как улучшить OCR/PDF/DXF обработку\n"
        "5. Риски и быстрые smoke tests\n"
    )


def run_deepseek_audit(df, *, file_name="", user_focus="", max_tokens=1800):
    if not deepseek_available():
        raise RuntimeError("DEEPSEEK_API_KEY is not configured.")

    prompt = build_deepseek_audit_prompt(df, file_name=file_name, user_focus=user_focus)
    answer = deepseek_chat(
        [
            {
                "role": "system",
                "content": (
                    "You are an expert reviewer of OCR, CAD text extraction, translation pipelines, "
                    "and engineering terminology localization. Answer in Russian."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=max_tokens,
    )
    return {
        "prompt": prompt,
        "answer": answer,
    }
