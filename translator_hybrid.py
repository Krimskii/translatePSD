import logging
import re

from normative_dictionary import sync_normative_candidates
from apply_cad_dict import apply_cad_dict
from post_translate_fix import cleanup_translation, finalize_translation, has_chinese
from section_dictionary import apply_section_terms, detect_section_for_text, translate_structured_cn_text
from translation_memory import (
    clean_memory,
    get_memory_translation_from_store,
    load_memory,
    save_memory,
    update_memory_entry_in_store,
)
from translation_router import build_translation_plan, normalize_source_text
from translator_batch import ollama_batch, ollama_translate_one
from translator_deepseek import deepseek_available, deepseek_translate


LOGGER = logging.getLogger(__name__)
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LATIN_ONLY_RE = re.compile(r"^[A-Za-z0-9\s,.;:()/%×\-–—_]+$")
PUNCT_ONLY_RE = re.compile(r"^[\s\d,.;:()/%×\-–—_]+$")
MEANINGFUL_TOKEN_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+")
CHINESE_GROUP_RE = re.compile(r"[\u4e00-\u9fff]+")


def _cyrillic_ratio(text):
    value = str(text)
    if not value:
        return 0.0
    cyr = len(CYRILLIC_RE.findall(value))
    return cyr / max(len(value), 1)


def _looks_model_explanatory(candidate):
    lowered = str(candidate).strip().lower()
    prefixes = (
        "перевод:",
        "translation:",
        "here is",
        "объяснение",
        "note:",
        "примечание:",
    )
    return lowered.startswith(prefixes)


def _looks_suspicious(source_text, candidate):
    source_text = str(source_text).strip()
    candidate, _, _ = finalize_translation(source_text, str(candidate).strip())

    if not candidate:
        return True
    if _looks_model_explanatory(candidate):
        return True
    if PUNCT_ONLY_RE.match(candidate):
        return True

    source_has_chinese = has_chinese(source_text)
    candidate_has_chinese = has_chinese(candidate)

    if candidate_has_chinese and source_has_chinese:
        return True
    if candidate_has_chinese and not source_has_chinese:
        return True

    source_len = len(source_text)
    candidate_len = len(candidate)
    source_groups = _chinese_group_count(source_text)
    candidate_tokens = _meaningful_token_count(candidate)

    if source_has_chinese and source_len >= 20 and candidate_len < max(8, int(source_len * 0.22)):
        return True
    if source_has_chinese and source_len >= 20 and _cyrillic_ratio(candidate) < 0.12:
        return True
    if source_has_chinese and LATIN_ONLY_RE.match(candidate) and _cyrillic_ratio(candidate) == 0:
        return True
    if source_groups >= 3 and candidate_tokens < min(3, source_groups):
        return True
    if ("（" in source_text or "(" in source_text) and candidate_tokens < 3:
        return True
    if source_text.count("，") + source_text.count(",") >= 2 and candidate_tokens < 3:
        return True

    return False


def _meaningful_content_ratio(text):
    value = str(text).strip()
    if not value:
        return 0.0
    meaningful = sum(len(token) for token in MEANINGFUL_TOKEN_RE.findall(value))
    return meaningful / max(len(value), 1)


def _meaningful_token_count(text):
    return len(MEANINGFUL_TOKEN_RE.findall(str(text)))


def _chinese_group_count(text):
    return len(CHINESE_GROUP_RE.findall(str(text)))


def _accept_dictionary_result(source_text, candidate, *, section):
    source_text = str(source_text).strip()
    candidate, _, _ = finalize_translation(source_text, str(candidate).strip(), section)
    if _looks_suspicious(source_text, candidate):
        return False
    candidate_ratio = _meaningful_content_ratio(candidate)
    if candidate_ratio < 0.35:
        return False
    if section == "UNKNOWN" and candidate_ratio < 0.5:
        return False
    chinese_groups = _chinese_group_count(source_text)
    candidate_tokens = _meaningful_token_count(candidate)
    if chinese_groups >= 3 and candidate_tokens < 2:
        return False
    if ("（" in source_text or "(" in source_text) and candidate_tokens < 2:
        return False
    if source_text.count("，") + source_text.count(",") >= 2 and candidate_tokens < 2:
        return False
    return len(candidate) >= max(4, int(len(source_text) * 0.18))


def _should_use_deepseek_first(text):
    value = str(text).strip()
    if not deepseek_available() or not has_chinese(value):
        return False
    if len(value) >= 200:
        return True
    if value.count("，") + value.count(",") >= 5:
        return True
    if value.count("。") + value.count(";") + value.count("；") >= 2:
        return True
    return "\n" in value and len(value) >= 120


def _memory_first_candidate(source_text, section, memory):
    source_text = str(source_text).strip()
    memory_hit = get_memory_translation_from_store(memory, source_text, section)
    if memory_hit:
        cleaned, _, _ = finalize_translation(source_text, memory_hit, section)
        return cleaned, "memory"

    source_with_terms, _, _ = finalize_translation(source_text, apply_section_terms(source_text, section), section)
    short_label = len(source_text) <= 40
    if short_label and source_with_terms != source_text and _accept_dictionary_result(source_text, source_with_terms, section=section):
        return source_with_terms, "section_dict"

    return None, None


def _dictionary_fallback(source_text, section):
    source_text = str(source_text).strip()
    section_text, _, _ = finalize_translation(source_text, apply_section_terms(source_text, section), section)
    dict_text, _, _ = finalize_translation(source_text, apply_section_terms(apply_cad_dict(source_text), section), section)

    for candidate in (section_text, dict_text):
        if candidate != source_text and _accept_dictionary_result(source_text, candidate, section=section):
            return candidate, "section_dict"

    return None, None


def _deepseek_candidate(source_text, section):
    if not deepseek_available():
        return None, None

    try:
        candidate, _, _ = finalize_translation(source_text, apply_section_terms(deepseek_translate(source_text), section), section)
    except Exception as exc:
        LOGGER.warning("DeepSeek translation failed: %s", exc)
        return None, None

    if _looks_suspicious(source_text, candidate):
        return None, None
    return candidate, "deepseek"


def _translate_cn_chunk(chunk, section):
    chunk = str(chunk).strip()
    if not chunk:
        return None

    candidate, _, _ = finalize_translation(chunk, apply_section_terms(ollama_translate_one(chunk), section), section)
    if not candidate or has_chinese(candidate) or _meaningful_token_count(candidate) < 1:
        if deepseek_available():
            try:
                candidate, _, _ = finalize_translation(chunk, apply_section_terms(deepseek_translate(chunk), section), section)
            except Exception as exc:
                LOGGER.warning("DeepSeek chunk translation failed: %s", exc)
                return None
        else:
            return None

    if not candidate or has_chinese(candidate) or _meaningful_token_count(candidate) < 1:
        return None
    return candidate


def _structured_fallback(source_text, section):
    source_text = str(source_text).strip()
    candidate, _, _ = finalize_translation(
        source_text,
        translate_structured_cn_text(
            source_text,
            section,
            on_missing=lambda chunk: _translate_cn_chunk(chunk, section),
        ),
        section,
    )
    if candidate == source_text:
        return None, None
    if has_chinese(candidate):
        return None, None
    if _looks_suspicious(source_text, candidate):
        return None, None
    return candidate, "structured_fallback"


def _translate_one(source_text, model_text, section, memory):
    source_text = str(source_text).strip()
    memory_candidate, memory_source = _memory_first_candidate(source_text, section, memory)
    if memory_candidate:
        return memory_candidate, memory_source

    if _should_use_deepseek_first(source_text):
        deepseek_text, source_name = _deepseek_candidate(source_text, section)
        if deepseek_text:
            update_memory_entry_in_store(memory, source_text, deepseek_text, section)
            return deepseek_text, source_name

    candidate, _, _ = finalize_translation(source_text, apply_section_terms(model_text, section), section)
    if not _looks_suspicious(source_text, candidate):
        update_memory_entry_in_store(memory, source_text, candidate, section)
        return candidate, "ollama"

    retry_text, _, _ = finalize_translation(source_text, apply_section_terms(ollama_translate_one(source_text), section), section)
    if not _looks_suspicious(source_text, retry_text):
        update_memory_entry_in_store(memory, source_text, retry_text, section)
        return retry_text, "ollama_retry"

    deepseek_text, deepseek_source = _deepseek_candidate(source_text, section)
    if deepseek_text:
        update_memory_entry_in_store(memory, source_text, deepseek_text, section)
        return deepseek_text, deepseek_source

    structured_text, structured_source = _structured_fallback(source_text, section)
    if structured_text:
        update_memory_entry_in_store(memory, source_text, structured_text, section)
        return structured_text, structured_source

    dict_text, dict_source = _dictionary_fallback(source_text, section)
    if dict_text:
        update_memory_entry_in_store(memory, source_text, dict_text, section)
        return dict_text, dict_source

    final_value = retry_text if retry_text.strip() else candidate or source_text
    update_memory_entry_in_store(memory, source_text, final_value, section)
    return final_value, "fallback"


def _resolve_batch_size(texts):
    max_len = max((len(t) for t in texts), default=0)
    avg_len = (sum(len(t) for t in texts) / len(texts)) if texts else 0

    if max_len <= 80 and avg_len <= 45:
        return 18
    if max_len <= 160 and avg_len <= 80:
        return 12
    if max_len >= 700 or avg_len >= 260:
        return 2
    if max_len >= 420 or avg_len >= 180:
        return 3
    if max_len >= 260 or avg_len >= 120:
        return 5
    return 8


def _pending_complexity(item):
    text = str(item["text"])
    length = len(text)
    punctuation = text.count("，") + text.count(",") + text.count("。") + text.count(";") + text.count("；")
    if length >= 700 or punctuation >= 8:
        return 4
    if length >= 420 or punctuation >= 5:
        return 3
    if length >= 180 or punctuation >= 3:
        return 2
    if length >= 80:
        return 1
    return 0


def _iter_pending_batches(pending_items):
    buckets = {}
    for item in pending_items:
        buckets.setdefault(_pending_complexity(item), []).append(item)

    for complexity in sorted(buckets):
        bucket = sorted(buckets[complexity], key=lambda item: len(str(item["text"])))
        batch_size = _resolve_batch_size([item["text"] for item in bucket])
        for start in range(0, len(bucket), batch_size):
            yield bucket[start : start + batch_size], batch_size, complexity


def _collect_qc_flags(source_text, translated_text):
    flags = []
    cleaned_text, untranslated, cleanup_flags = finalize_translation(source_text, translated_text)
    if untranslated:
        flags.append("contains_chinese")
    flags.extend(cleanup_flags)
    if _looks_suspicious(source_text, cleaned_text):
        flags.append("low_quality")
    return ",".join(sorted(set(flag for flag in flags if flag)))


def translate_df(df):
    working_df = df.copy()
    texts = [normalize_source_text(text) for text in working_df["text"].astype(str).tolist()]
    total = len(texts)
    sections = [detect_section_for_text(text) for text in texts]
    memory, removed_bad_memory = clean_memory(load_memory())
    if removed_bad_memory:
        LOGGER.info("Removed %s bad translation-memory entries", removed_bad_memory)

    plan = build_translation_plan(texts, sections, memory)
    translated = plan["translated"]
    sources = plan["sources"]
    untranslated = plan["untranslated"]
    qc_flags = plan["qc_flags"]
    unique_pending = plan["pending"]
    LOGGER.info("Translation routing stats: %s", plan["stats"])

    LOGGER.info("Translating %s unique rows with dynamic batches", len(unique_pending))

    processed_unique = 0
    for batch_items, batch_size, complexity in _iter_pending_batches(unique_pending):
        batch = [item["text"] for item in batch_items]
        LOGGER.info(
            "batch %s / %s, size=%s, complexity=%s",
            processed_unique,
            len(unique_pending),
            batch_size,
            complexity,
        )

        try:
            model_results = ollama_batch(batch)
        except Exception as exc:
            LOGGER.warning("Ollama batch failed: %s", exc)
            model_results = batch

        if len(model_results) != len(batch):
            LOGGER.warning("Batch size mismatch from model: %s != %s", len(model_results), len(batch))
            model_results = batch

        for item, model_text in zip(batch_items, model_results):
            translated_text, source_name = _translate_one(item["text"], model_text, item["section"], memory)
            flags = _collect_qc_flags(item["text"], translated_text)
            has_leftover = has_chinese(translated_text)

            for row_idx in item["rows"]:
                translated[row_idx] = translated_text
                sources[row_idx] = source_name if row_idx == item["rows"][0] else f"{source_name}_duplicate"
                untranslated[row_idx] = has_leftover
                qc_flags[row_idx] = flags
        processed_unique += len(batch_items)

    for idx, original in enumerate(texts):
        if translated[idx] is None:
            translated[idx] = original
        if sources[idx] is None:
            sources[idx] = "fallback"
        if sources[idx] == "passthrough":
            translated[idx] = original
            untranslated[idx] = False
            qc_flags[idx] = qc_flags[idx] or ""
            working_df.at[idx, "cleaned_translated"] = original
            continue
        cleaned_text, has_leftover, cleanup_flags = finalize_translation(original, translated[idx], sections[idx])
        translated[idx] = cleaned_text
        working_df.at[idx, "cleaned_translated"] = cleaned_text if "cleaned_translated" in working_df.columns else cleaned_text
        extra_flags = set(filter(None, (qc_flags[idx] or "").split(","))) if qc_flags[idx] else set()
        extra_flags.update(cleanup_flags)
        if not extra_flags:
            merged_flags = _collect_qc_flags(original, cleaned_text)
        else:
            merged_flags = ",".join(sorted(extra_flags | set(filter(None, _collect_qc_flags(original, cleaned_text).split(",")))))
        qc_flags[idx] = merged_flags
        untranslated[idx] = has_leftover

    save_memory(memory)
    working_df["text"] = texts
    working_df["translated"] = translated
    working_df["cleaned_translated"] = translated
    working_df["section"] = sections
    working_df["translation_source"] = sources
    working_df["untranslated_chinese"] = untranslated
    working_df["qc_flags"] = qc_flags
    sync_normative_candidates(working_df)
    return working_df
