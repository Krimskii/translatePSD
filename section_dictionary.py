import json
import os
import re
from functools import lru_cache

from normative_dictionary import apply_normative_terms, load_normative_dictionary
from validator_sections import detect_section


SECTION_TERMS_PATH = os.getenv("SECTION_TERMS_PATH", "dictionary/section_terms_seed.json")
CHINESE_GROUP_RE = re.compile(r"[\u4e00-\u9fff]+")
SECTION_TERMS_FALLBACK = {
    "ТХ": {
        "工艺": "технология",
        "流程": "технологический процесс",
        "原料": "сырье",
        "挤压": "прессование",
        "包装": "упаковка",
    },
    "ОВ": {
        "通风": "вентиляция",
        "排风": "вытяжка",
        "送风": "приток",
        "风管": "воздуховод",
    },
    "ВК": {
        "给排水": "водоснабжение и канализация",
        "排水沟": "водоотводный лоток",
        "污水沟": "лоток сточных вод",
    },
    "ЭОМ": {
        "电气": "электроснабжение",
        "桥架": "кабельный лоток",
    },
    "КЖ": {
        "钢构柱": "стальная колонна",
        "柱面": "грань колонны",
    },
    "АР": {
        "车间门": "дверь цеха",
        "总平面": "генеральный план",
    },
    "UNKNOWN": {
        "原料": "сырье",
        "辅料": "вспомогательные материалы",
    },
}


@lru_cache(maxsize=1)
def load_section_terms():
    if os.path.exists(SECTION_TERMS_PATH):
        with open(SECTION_TERMS_PATH, "r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    return SECTION_TERMS_FALLBACK


def detect_section_for_text(text):
    text = str(text)
    section = detect_section(text)
    terms = load_section_terms()
    return section if section in terms else "UNKNOWN"


def build_section_term_map(section=None):
    section_name = str(section or "").strip() or "UNKNOWN"
    merged_terms = dict(load_section_terms().get(section_name, {}))

    for source, target in load_normative_dictionary().get("ALL", {}).items():
        merged_terms[source] = target

    for source, target in load_normative_dictionary().get(section_name, {}).items():
        merged_terms[source] = target

    return merged_terms


def _translate_chunk_with_terms(chunk, term_map):
    value = str(chunk)
    if value in term_map:
        return term_map[value]

    for source, target in sorted(term_map.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(source, target)
    return value


def translate_structured_cn_text(text, section=None, on_missing=None):
    value = str(text)
    section_name = section or detect_section_for_text(value)
    term_map = build_section_term_map(section_name)
    tokens = re.split(r"([\u4e00-\u9fff]+)", value)
    translated_tokens = []

    for token in tokens:
        if not token:
            continue
        if CHINESE_GROUP_RE.fullmatch(token):
            translated = _translate_chunk_with_terms(token, term_map)
            if CHINESE_GROUP_RE.search(translated) and on_missing:
                recovered = on_missing(token)
                if recovered:
                    translated = recovered
            translated_tokens.append(translated)
        else:
            translated_tokens.append(token)

    return "".join(translated_tokens)


def apply_section_terms(text, section=None):
    value = str(text)
    section_name = section or detect_section_for_text(value)
    merged_terms = build_section_term_map(section_name)

    for source, target in sorted(merged_terms.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(source, target)

    return apply_normative_terms(value, section_name)
