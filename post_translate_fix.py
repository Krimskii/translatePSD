import re


CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")

PHRASE_REPLACEMENTS = {
    "车间门": "дверь цеха",
    "以钢构柱面为准": "по грани стальной колонны",
    "600x400方井": "600x400 квадратный колодец",
    "600X400方井": "600x400 квадратный колодец",
    "也可以圆井": "допускается круглый колодец",
    "行车牛腿": "подкрановая консоль",
    "喷雾机水与模具冷凝污水沟": "лоток сточных вод от распылительной установки и конденсата форм",
    "深度200mm": "глубина 200 мм",
    "排水沟外围300mm以上水泥浇筑": "бетонная заливка по периметру водоотводного лотка шириной не менее 300 мм",
    "方井": "квадратный колодец",
    "圆井": "круглый колодец",
    "污水沟": "лоток сточных вод",
    "排水沟": "водоотводный лоток",
    "钢构柱": "стальная колонна",
    "柱面": "грань колонны",
    "喷雾机": "распылительная установка",
    "模具": "форма",
    "冷凝": "конденсат",
    "牛腿": "консоль",
    "行车": "мостовой кран",
    "车间": "цех",
    "门": "дверь",
    "基础": "фундамент",
}

TOKEN_REPLACEMENTS = {
    "镀锌管": "оцинкованная труба",
    "井": "колодец",
    "泵": "насос",
    "管": "труба",
    "阀": "клапан",
    "沟": "лоток",
    "污水": "сточные воды",
    "雨水": "дождевые воды",
    "柱": "колонна",
    "梁": "балка",
}

MIXED_OUTPUT_REPLACEMENTS = {
    "квадратная яма": "квадратный колодец",
    "круглая яма": "круглый колодец",
    "также можно круглая яма": "допускается круглый колодец",
    "входные двери цеха": "дверь цеха",
    "ножки行车": "подкрановая консоль",
    "ножки行车腿": "подкрановая консоль",
    "water spray": "распылительная установка",
    "spray machine": "распылительная установка",
    "spray": "распылительная",
}


def has_chinese(text):
    return bool(CHINESE_RE.search(str(text)))


def _apply_mapping(text, mapping):
    value = str(text)
    for source in sorted(mapping, key=len, reverse=True):
        value = value.replace(source, mapping[source])
    return value


def replace_known_terms(text):
    value = _apply_mapping(text, PHRASE_REPLACEMENTS)
    value = _apply_mapping(value, TOKEN_REPLACEMENTS)
    value = _apply_mapping(value, MIXED_OUTPUT_REPLACEMENTS)
    return value


def cleanup_translation(text):
    value = replace_known_terms(str(text).strip())

    # Remove leftover isolated Chinese symbols after phrase substitutions.
    value = CHINESE_RE.sub(" ", value)
    value = value.replace("_", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,.;:])", r"\1", value)
    value = value.strip(" -_")

    return value
