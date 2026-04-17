import re

import pandas as pd

from apply_cad_dict import apply_cad_dict
from post_translate_fix import cleanup_translation, has_chinese
from translator_batch import ollama_batch, ollama_translate_one
from translator_deepseek import deepseek_available, deepseek_translate


CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
PUNCT_ONLY_RE = re.compile(r"^[\s\d,.;:()/%×\-–—_]+$")


def _cyrillic_ratio(text):
    value = str(text)
    if not value:
        return 0.0
    cyr = len(CYRILLIC_RE.findall(value))
    return cyr / max(len(value), 1)


def _looks_suspicious(source_text, candidate):
    source_text = str(source_text)
    candidate = str(candidate).strip()

    if not candidate:
        return True

    if PUNCT_ONLY_RE.match(candidate):
        return True

    if has_chinese(candidate):
        return True

    if has_chinese(source_text):
        source_len = len(source_text.strip())
        candidate_len = len(candidate)

        if source_len >= 20 and candidate_len < max(8, int(source_len * 0.2)):
            return True

        if source_len >= 20 and _cyrillic_ratio(candidate) < 0.12:
            return True

    return False


def _translate_one(source_text, model_text):
    source_text = str(source_text)
    candidate = cleanup_translation(model_text)

    if not candidate:
        candidate = source_text

    if not _looks_suspicious(source_text, candidate):
        return candidate

    retry_text = cleanup_translation(ollama_translate_one(source_text))
    if not _looks_suspicious(source_text, retry_text):
        return retry_text

    dict_fallback = cleanup_translation(apply_cad_dict(source_text))
    short_label = len(source_text) <= 30
    if short_label and dict_fallback != source_text and not _looks_suspicious(source_text, dict_fallback):
        return dict_fallback

    if deepseek_available():
        try:
            deepseek_text = cleanup_translation(deepseek_translate(source_text))
            if not _looks_suspicious(source_text, deepseek_text):
                return deepseek_text
        except Exception as e:
            print("deepseek error:", e)

    if short_label and dict_fallback != source_text:
        return dict_fallback

    return retry_text if retry_text.strip() else candidate


def translate_df(df):
    texts = df["text"].astype(str).tolist()
    texts = [t[:1200] for t in texts]

    batch_size = 12
    translated = []
    total = len(texts)

    for i in range(0, total, batch_size):
        print(f"batch {i} / {total}")

        batch = texts[i : i + batch_size]

        try:
            result = ollama_batch(batch)
        except Exception as e:
            print("ollama error:", e)
            result = batch

        if len(result) != len(batch):
            result = batch

        fixed = []
        for source_text, model_text in zip(batch, result):
            fixed.append(_translate_one(source_text, model_text))

        translated.extend(fixed)

    if len(translated) != len(df):
        translated = translated[: len(df)]

        while len(translated) < len(df):
            translated.append(df["text"].iloc[len(translated)])

    df["translated"] = translated
    return df
