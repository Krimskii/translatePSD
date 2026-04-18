import logging
import os
import re
from typing import Iterable

import requests

from post_translate_fix import cleanup_translation, has_chinese


LOGGER = logging.getLogger(__name__)
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "240"))
MAX_BATCH_RESPONSE_TOKENS = int(os.getenv("OLLAMA_BATCH_NUM_PREDICT", "1200"))
MAX_SINGLE_RESPONSE_TOKENS = int(os.getenv("OLLAMA_SINGLE_NUM_PREDICT", "1400"))
SEPARATOR = "\n@@ROW@@\n"
NOISE_RE = re.compile(r"^(?:here(?: is|'s)|translation|перевод|объяснение)\b", re.IGNORECASE)


def _build_session():
    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


SESSION = _build_session()


def _generate(prompt, *, num_predict):
    response = SESSION.post(
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
                "stop": [SEPARATOR.strip()],
            },
        },
        timeout=OLLAMA_TIMEOUT,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload.get("response", ""))


def _sanitize_model_output(value):
    text = cleanup_translation(str(value).strip())
    if NOISE_RE.match(text):
        return ""
    text = text.replace("```", "").strip()
    return text


def _normalize_batch_lines(lines: Iterable[str], expected_count: int):
    cleaned = [_sanitize_model_output(item) for item in lines]
    cleaned = [item for item in cleaned]
    if len(cleaned) != expected_count:
        return None
    return cleaned


def _split_batch_response(raw_response, expected_count):
    raw = str(raw_response).strip()
    if not raw:
        return None

    if SEPARATOR.strip() in raw:
        parts = raw.split(SEPARATOR.strip())
        normalized = _normalize_batch_lines(parts, expected_count)
        if normalized:
            return normalized

    if SEPARATOR in raw:
        parts = raw.split(SEPARATOR)
        normalized = _normalize_batch_lines(parts, expected_count)
        if normalized:
            return normalized

    numbered_parts = re.split(r"\n\s*(?:\d+[\).:]\s+)", f"\n{raw}")
    numbered_parts = [item.strip() for item in numbered_parts if item.strip()]
    normalized = _normalize_batch_lines(numbered_parts, expected_count)
    if normalized:
        return normalized

    newline_parts = [item.strip() for item in raw.splitlines() if item.strip()]
    normalized = _normalize_batch_lines(newline_parts, expected_count)
    if normalized:
        return normalized

    return None


def ollama_batch(texts):
    rows = [str(text).strip() for text in texts]
    if not rows:
        return []

    prompt_rows = [f"[{index + 1}]{row}" for index, row in enumerate(rows)]
    prompt = (
        "Translate each Chinese engineering row into concise Russian.\n"
        "Return exactly the same number of rows in the same order.\n"
        f"Use the separator {SEPARATOR.strip()} between rows.\n"
        "Do not explain, do not comment, do not add headings.\n"
        "If a row is already non-Chinese, return it unchanged.\n\n"
        f"{SEPARATOR.join(prompt_rows)}"
    )

    try:
        raw_response = _generate(prompt, num_predict=MAX_BATCH_RESPONSE_TOKENS)
        parsed = _split_batch_response(raw_response, len(rows))
        if parsed:
            return [item or source for item, source in zip(parsed, rows)]

        LOGGER.warning("Batch response length mismatch; falling back to row-by-row translation.")
    except Exception as exc:
        LOGGER.warning("Ollama batch failed: %s", exc)

    return [ollama_translate_one(text) for text in rows]


def ollama_translate_one(text):
    source_text = str(text).strip()
    if not source_text:
        return ""

    prompt = (
        "Translate the following Chinese engineering / CAD text into Russian.\n"
        "Rules:\n"
        "- only translated text\n"
        "- keep numbers, units, abbreviations, dimensions\n"
        "- no commentary or explanation\n"
        "- if the source is not Chinese, return it as-is\n\n"
        f"TEXT:\n{source_text}"
    )

    try:
        translated = _sanitize_model_output(_generate(prompt, num_predict=MAX_SINGLE_RESPONSE_TOKENS))
        if not translated:
            return source_text
        if has_chinese(translated) and not has_chinese(source_text):
            return source_text
        return translated
    except Exception as exc:
        LOGGER.warning("Ollama single failed: %s", exc)
        return source_text
