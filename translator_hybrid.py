import re

import pandas as pd

from normative_dictionary import sync_normative_candidates
from apply_cad_dict import apply_cad_dict
from post_translate_fix import cleanup_translation, has_chinese
from section_dictionary import apply_section_terms, detect_section_for_text
from translation_memory import (
    get_memory_translation_from_store,
    load_memory,
    save_memory,
    update_memory_entry_in_store,
)
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


def _should_use_deepseek_first(text):
    value = str(text).strip()
    if not deepseek_available():
        return False

    if not has_chinese(value):
        return False

    if len(value) >= 180:
        return True

    if value.count("，") + value.count(",") >= 4:
        return True

    if value.count("。") + value.count(";") + value.count("；") >= 2:
        return True

    if "\n" in value and len(value) >= 120:
        return True

    return False


def _memory_first_candidate(source_text, section, memory):
    source_text = str(source_text)
    memory_hit = get_memory_translation_from_store(memory, source_text, section)
    if memory_hit:
        return memory_hit, "memory"

    source_with_terms = cleanup_translation(apply_section_terms(source_text, section))
    short_label = len(source_text.strip()) <= 40

    if short_label and source_with_terms != source_text and not _looks_suspicious(source_text, source_with_terms):
        return source_with_terms, "section_dict"

    return None, None


def _translate_one(source_text, model_text, section, memory):
    source_text = str(source_text)
    memory_candidate, memory_source = _memory_first_candidate(source_text, section, memory)
    if memory_candidate:
        return memory_candidate, memory_source

    source_with_terms = apply_section_terms(source_text, section)

    if _should_use_deepseek_first(source_text):
        try:
            deepseek_text = cleanup_translation(apply_section_terms(deepseek_translate(source_text), section))
            if not _looks_suspicious(source_text, deepseek_text):
                update_memory_entry_in_store(memory, source_text, deepseek_text, section)
                return deepseek_text, "deepseek"
        except Exception as e:
            print("deepseek preflight error:", e)

    candidate = cleanup_translation(apply_section_terms(model_text, section))

    if not candidate:
        candidate = source_with_terms

    if not _looks_suspicious(source_text, candidate):
        update_memory_entry_in_store(memory, source_text, candidate, section)
        return candidate, "ollama"

    retry_text = cleanup_translation(apply_section_terms(ollama_translate_one(source_text), section))
    if not _looks_suspicious(source_text, retry_text):
        update_memory_entry_in_store(memory, source_text, retry_text, section)
        return retry_text, "ollama_retry"

    dict_fallback = cleanup_translation(apply_section_terms(apply_cad_dict(source_text), section))
    short_label = len(source_text) <= 30
    if short_label and dict_fallback != source_text and not _looks_suspicious(source_text, dict_fallback):
        update_memory_entry_in_store(memory, source_text, dict_fallback, section)
        return dict_fallback, "section_dict"

    if deepseek_available():
        try:
            deepseek_text = cleanup_translation(apply_section_terms(deepseek_translate(source_text), section))
            if not _looks_suspicious(source_text, deepseek_text):
                update_memory_entry_in_store(memory, source_text, deepseek_text, section)
                return deepseek_text, "deepseek"
        except Exception as e:
            print("deepseek error:", e)

    if short_label and dict_fallback != source_text:
        update_memory_entry_in_store(memory, source_text, dict_fallback, section)
        return dict_fallback, "section_dict"

    final_value = retry_text if retry_text.strip() else candidate
    update_memory_entry_in_store(memory, source_text, final_value, section)
    return final_value, "fallback"


def _resolve_batch_size(texts):
    max_len = max((len(t) for t in texts), default=0)
    avg_len = (sum(len(t) for t in texts) / len(texts)) if texts else 0

    if max_len >= 500 or avg_len >= 220:
        return 3
    if max_len >= 280 or avg_len >= 140:
        return 5
    return 8


def translate_df(df):
    texts = df["text"].astype(str).tolist()
    texts = [t[:1200] for t in texts]
    total = len(texts)
    sections = [detect_section_for_text(text) for text in texts]
    memory = load_memory()
    translated = [None] * total
    sources = [None] * total
    unique_pending = []
    unique_index = {}

    for idx, (text, section) in enumerate(zip(texts, sections)):
        cached_text, cached_source = _memory_first_candidate(text, section, memory)
        if cached_text:
            translated[idx] = cached_text
            sources[idx] = cached_source
            continue

        key = (section, text)
        if key not in unique_index:
            unique_index[key] = len(unique_pending)
            unique_pending.append({"section": section, "text": text, "rows": [idx]})
        else:
            unique_pending[unique_index[key]]["rows"].append(idx)

    pending_texts = [item["text"] for item in unique_pending]
    batch_size = _resolve_batch_size(pending_texts)

    for i in range(0, len(unique_pending), batch_size):
        print(f"batch {i} / {len(unique_pending)}")
        batch_items = unique_pending[i : i + batch_size]
        batch = [item["text"] for item in batch_items]

        try:
            result = ollama_batch(batch)
        except Exception as e:
            print("ollama error:", e)
            result = batch

        if len(result) != len(batch):
            result = batch

        for item, model_text in zip(batch_items, result):
            translated_text, source_name = _translate_one(item["text"], model_text, item["section"], memory)
            for row_idx in item["rows"]:
                translated[row_idx] = translated_text
                sources[row_idx] = source_name if row_idx == item["rows"][0] else f"{source_name}_duplicate"

    for idx, original in enumerate(df["text"].tolist()):
        if translated[idx] is None:
            translated[idx] = original
        if sources[idx] is None:
            sources[idx] = "fallback"

    save_memory(memory)
    df["translated"] = translated
    df["section"] = sections
    df["translation_source"] = sources
    sync_normative_candidates(df)
    return df
