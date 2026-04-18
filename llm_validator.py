import logging
import os

import requests

from post_translate_fix import cleanup_translation, has_chinese
from translator_hybrid import _looks_suspicious


LOGGER = logging.getLogger(__name__)
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "240"))


def _generate(prompt, *, num_predict=700):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": num_predict,
                "top_p": 1,
                "repeat_penalty": 1.05,
            },
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("response", ""))


def _should_review_row(row):
    translated = str(row.get("translated", "")).strip()
    source_text = str(row.get("text", "")).strip()
    qc_flags = str(row.get("qc_flags", "")).strip()

    if not translated:
        return True
    if bool(row.get("untranslated_chinese", False)):
        return True
    if qc_flags:
        return True
    if _looks_suspicious(source_text, translated):
        return True
    return False


def _review_one(source_text, current_translation, section="UNKNOWN"):
    source_text = str(source_text).strip()
    current_translation = str(current_translation).strip()
    prompt = (
        "You are validating a Russian translation of Chinese engineering documentation.\n"
        "Your task is to minimally edit the Russian text so that it is faithful to the source Chinese.\n"
        "Rules:\n"
        "- do not add any new facts not present in the source\n"
        "- do not explain or comment\n"
        "- return only the corrected Russian translation\n"
        "- preserve numbers, units, dimensions, sequence numbering\n"
        "- keep the output concise and engineering-style\n"
        "- if the current translation is already acceptable, return it with only necessary fixes\n\n"
        f"SECTION: {section}\n"
        f"SOURCE_CN:\n{source_text}\n\n"
        f"CURRENT_RU:\n{current_translation}\n"
    )

    try:
        candidate = cleanup_translation(_generate(prompt))
    except Exception as exc:
        LOGGER.warning("LLM validator failed: %s", exc)
        return current_translation, False

    if not candidate:
        return current_translation, False
    if has_chinese(candidate):
        return current_translation, False
    if _looks_suspicious(source_text, candidate):
        return current_translation, False
    if candidate == current_translation:
        return current_translation, False
    return candidate, True


def llm_validate_and_edit_df(df, *, only_flagged=True):
    working_df = df.copy()
    edited = 0
    validation_source = []

    for _, row in working_df.iterrows():
        needs_review = _should_review_row(row) if only_flagged else True
        if not needs_review:
            validation_source.append("")
            continue

        current = str(row.get("normalized", row.get("translated", ""))).strip()
        reviewed, changed = _review_one(
            row.get("text", ""),
            current,
            section=row.get("section", "UNKNOWN"),
        )

        if changed:
            if "normalized" in working_df.columns and str(row.get("normalized", "")).strip():
                row_index = row.name
                working_df.at[row_index, "normalized"] = reviewed
            else:
                row_index = row.name
                working_df.at[row_index, "translated"] = reviewed
            edited += 1
            validation_source.append("llm_validator")
        else:
            validation_source.append("")

    working_df["llm_validation_source"] = validation_source
    LOGGER.info("LLM validator edited %s rows", edited)
    return working_df, edited
