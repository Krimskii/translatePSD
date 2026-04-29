import hashlib
import re

from post_translate_fix import finalize_translation, has_chinese
from section_dictionary import apply_section_terms, detect_section_for_text, translate_structured_cn_text
from translation_memory import get_memory_translation_from_store


CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
LETTER_RE = re.compile(r"[\u4e00-\u9fffA-Za-zА-Яа-яЁё]")
MEANINGFUL_TOKEN_RE = re.compile(r"[А-Яа-яЁёA-Za-z]{2,}")
NUMERIC_OR_CAD_RE = re.compile(
    r"""
    ^[\s\d
    .,\-+−–—_=:/\\|#№()\[\]{}<>*
    xX×Øø°'"\u2032\u2033
    %‰
    mMмМcCсСkKкКgGгГtTтТnNнНpPпПaAаАvVвВwWвВhHчЧ
    ]+$
    """,
    re.VERBOSE,
)
CAD_CODE_RE = re.compile(r"^[A-Za-zА-Яа-я]{0,4}[-_/]?\d+[A-Za-zА-Яа-я0-9\-_/]*$")


def normalize_source_text(text, *, max_len=1400):
    return re.sub(r"\s+", " ", str(text or "")).strip()[:max_len]


def stable_text_hash(text):
    return hashlib.sha1(normalize_source_text(text).encode("utf-8")).hexdigest()


def is_passthrough_text(text):
    value = normalize_source_text(text)
    if not value:
        return True
    if has_chinese(value):
        return False
    if not LETTER_RE.search(value):
        return True

    compact = re.sub(r"\s+", "", value)
    if NUMERIC_OR_CAD_RE.fullmatch(compact):
        return True
    if CAD_CODE_RE.fullmatch(compact):
        return True
    if CYRILLIC_RE.search(value):
        return True

    # Keep short CAD abbreviations/codes out of the model, but allow longer
    # English labels to be translated if the user wants fully Russian output.
    tokens = MEANINGFUL_TOKEN_RE.findall(value)
    return len(value) <= 12 and len(tokens) <= 1


def _is_good_dictionary_result(source_text, candidate):
    candidate = normalize_source_text(candidate)
    if not candidate or candidate == source_text:
        return False
    if has_chinese(candidate):
        return False
    if not MEANINGFUL_TOKEN_RE.search(candidate):
        return False
    source_groups = len(re.findall(r"[\u4e00-\u9fff]+", source_text))
    target_tokens = len(MEANINGFUL_TOKEN_RE.findall(candidate))
    if source_groups >= 3 and target_tokens < 2:
        return False
    return True


def resolve_fast_translation(source_text, section, memory):
    source_text = normalize_source_text(source_text)
    section = section or detect_section_for_text(source_text)

    if is_passthrough_text(source_text):
        return {
            "translated": source_text,
            "source": "passthrough",
            "untranslated": False,
            "qc_flags": [],
        }

    memory_hit = get_memory_translation_from_store(memory, source_text, section)
    if memory_hit:
        cleaned, untranslated, flags = finalize_translation(source_text, memory_hit, section)
        if not untranslated:
            return {
                "translated": cleaned,
                "source": "memory",
                "untranslated": untranslated,
                "qc_flags": flags,
            }

    structured = translate_structured_cn_text(source_text, section)
    structured, untranslated, flags = finalize_translation(source_text, structured, section)
    if _is_good_dictionary_result(source_text, structured):
        return {
            "translated": structured,
            "source": "structured_dict",
            "untranslated": untranslated,
            "qc_flags": flags,
        }

    terms = apply_section_terms(source_text, section)
    terms, untranslated, flags = finalize_translation(source_text, terms, section)
    if _is_good_dictionary_result(source_text, terms):
        return {
            "translated": terms,
            "source": "section_dict",
            "untranslated": untranslated,
            "qc_flags": flags,
        }

    return None


def build_translation_plan(texts, sections, memory):
    translated = [None] * len(texts)
    sources = [None] * len(texts)
    untranslated = [False] * len(texts)
    qc_flags = [""] * len(texts)
    pending = []
    pending_index = {}
    fast_cache = {}
    stats = {
        "rows": len(texts),
        "passthrough": 0,
        "memory": 0,
        "dictionary": 0,
        "duplicates": 0,
        "llm_unique": 0,
    }

    for idx, (text, section) in enumerate(zip(texts, sections)):
        key = (section, stable_text_hash(text))
        if key in fast_cache:
            fast = fast_cache[key]
        else:
            fast = resolve_fast_translation(text, section, memory)
            fast_cache[key] = fast

        if fast:
            translated[idx] = fast["translated"]
            sources[idx] = fast["source"]
            untranslated[idx] = fast["untranslated"]
            qc_flags[idx] = ",".join(fast["qc_flags"])
            if fast["source"] == "passthrough":
                stats["passthrough"] += 1
            elif fast["source"] == "memory":
                stats["memory"] += 1
            else:
                stats["dictionary"] += 1
            continue

        if key not in pending_index:
            pending_index[key] = len(pending)
            pending.append({"section": section, "text": text, "rows": [idx]})
        else:
            pending[pending_index[key]]["rows"].append(idx)
            stats["duplicates"] += 1

    stats["llm_unique"] = len(pending)
    return {
        "translated": translated,
        "sources": sources,
        "untranslated": untranslated,
        "qc_flags": qc_flags,
        "pending": pending,
        "stats": stats,
    }
