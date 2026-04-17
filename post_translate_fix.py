import re


CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

KNOWN_REPLACEMENTS = {
    "镀锌管": "оцинкованная труба",
    "井": "колодец",
    "泵": "насос",
    "管": "труба",
    "阀": "клапан",
    "沟": "канал",
    "污水": "сточные воды",
    "雨水": "дождевые воды",
    "基础": "фундамент",
    "柱": "колонна",
}


def has_chinese(text):
    return bool(CHINESE_RE.search(str(text)))


def replace_known_terms(text):
    value = str(text)
    for source, target in KNOWN_REPLACEMENTS.items():
        value = value.replace(source, target)
    return value


def cleanup_translation(text):
    return replace_known_terms(str(text).strip())
