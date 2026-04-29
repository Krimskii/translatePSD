import re

from section_dictionary import build_section_term_map, detect_section_for_text, translate_structured_cn_text


CHINESE_FRAGMENT_RE = re.compile(r"[\u4e00-\u9fff]+")
NUMBER_CN_UNIT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*([个只件套])")
PROMPT_LEAK_RE = re.compile(
    r"^\s*(?:rules?|правила)\s*:\s*.*?(?:text|текст)\s*:\s*",
    flags=re.IGNORECASE | re.DOTALL,
)
LEADING_RULE_LINE_RE = re.compile(
    r"^\s*(?:rules?|правила)\s*:.*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
LEADING_BULLET_RE = re.compile(
    r"^\s*[-•]\s*(?:keep|translate|return|do not|сохранять|перевести|не добавлять|вернуть).*$",
    flags=re.IGNORECASE | re.MULTILINE,
)
PUNCT_ONLY_RE = re.compile(r"^[\s\d,.;:()/%×\-–—_+\\[\]{}<>|]+$")
MEANINGFUL_TOKEN_RE = re.compile(r"[А-Яа-яЁёA-Za-z]+")

FULLWIDTH_PUNCT_MAP = str.maketrans(
    {
        "（": "(",
        "）": ")",
        "：": ":",
        "，": ",",
        "；": ";",
        "。": ".",
        "＋": "+",
        "、": ",",
    }
)

PHRASE_REPLACEMENTS = {
    "中国标准": "китайский стандарт",
    "个中": "в том числе",
    "从原料到成品": "от сырья до готовой продукции",
    "从原料到产品": "от сырья до готовой продукции",
    "铝材标准工业流程": "стандартный промышленный процесс алюминиевых изделий",
    "标准工业流程": "стандартный промышленный процесс",
    "工业流程说明": "описание промышленного процесса",
    "能源:电,天然气,水,压缩空气.": "Энергоносители: электроэнергия, природный газ, вода, сжатый воздух.",
    "能源: 电, 天然气, 水, 压缩空气.": "Энергоносители: электроэнергия, природный газ, вода, сжатый воздух.",
    "1:熔炼:铝锭+废料投入熔铸炉熔炼.": "1: Плавка: алюминиевый слиток и отходы загружаются в плавильно-литейную печь на плавку.",
    "1: 熔炼: 铝锭+废料投入熔铸炉熔炼.": "1: Плавка: алюминиевый слиток и отходы загружаются в плавильно-литейную печь на плавку.",
    "600x400方井": "600×400 квадратный смотровой колодец",
    "600X400方井": "600×400 квадратный смотровой колодец",
    "也可以圆井": "допускается устройство круглого смотрового колодца",
    "喷雾机水与模具冷凝污水沟": "лоток отвода сточных вод от распылительной установки и конденсата форм",
    "排水沟外围300mm以上水泥浇筑": "бетонная подготовка по периметру водоотводного лотка шириной не менее 300 мм",
    "深度200mm": "глубина 200 мм",
    "以钢构柱面为准": "привязать по грани стальной колонны",
    "车间门": "дверь цеха",
    "行车牛腿": "подкрановая консоль",
    "建筑铝材": "архитектурные алюминиевые конструкции",
    "工业铝材": "промышленные алюминиевые изделия",
}

TOKEN_REPLACEMENTS = {
    "个": "шт.",
    "只": "шт.",
    "件": "шт.",
    "套": "комплект",
    "中": "средний",
    "中国": "Китай",
    "单位": "единица измерения",
    "序号": "номер",
    "绿地率": "коэффициент озеленения",
    "容积率": "коэффициент плотности застройки",
    "建筑系数": "коэффициент застройки",
    "建筑物占地面积": "площадь застройки здания",
    "规划建设用地面积": "площадь земельного участка под строительство",
    "计容总建筑面积": "общая расчетная площадь застройки",
    "货车停车位": "машино-места для грузовых автомобилей",
    "小汽车停车位": "машино-места для легковых автомобилей",
    "能源": "Энергоносители",
    "电": "электроэнергия",
    "天然气": "природный газ",
    "水": "вода",
    "压缩空气": "сжатый воздух",
    "原料": "сырье",
    "主要原料": "основное сырье",
    "辅料": "вспомогательные материалы",
    "熔铸工段": "литейный участок",
    "熔铸": "литейный участок",
    "工段": "участок",
    "熔炼": "плавка",
    "铝锭": "алюминиевый слиток",
    "废料": "отходы",
    "废铝": "алюминиевый лом",
    "投入": "загружаются",
    "熔铸炉": "плавильно-литейная печь",
    "镁": "магний",
    "硅": "кремний",
    "合金元素": "легирующие элементы",
    "精炼剂": "рафинирующая добавка",
    "覆盖剂": "покровный флюс",
    "溶剂": "растворитель",
    "时效热处理": "термообработка старением",
    "保温": "выдержка",
    "提高硬度": "повышение твердости",
    "建筑铝材": "архитектурные алюминиевые конструкции",
    "工业铝材": "промышленные алюминиевые изделия",
    "门窗": "дверные и оконные конструкции",
    "幕墙": "витражные фасады",
    "阳光房": "зимние сады",
    "设备框架": "каркасы оборудования",
    "光伏支架": "опоры фотоэлектрических панелей",
    "汽车件": "автомобильные комплектующие",
    "废弃物": "отходы",
    "排放物": "выбросы",
    "全流程": "всего процесса",
    "产生": "образуется",
    "铝灰": "алюминиевая зола",
    "铝渣": "алюминиевый шлак",
    "方井": "квадратный смотровой колодец",
    "圆井": "круглый смотровой колодец",
    "污水沟": "лоток сточных вод",
    "排水沟": "водоотводный лоток",
}

MIXED_OUTPUT_REPLACEMENTS = {
    "квадратная яма": "квадратный смотровой колодец",
    "круглая яма": "круглый смотровой колодец",
    "входные двери цеха": "дверь цеха",
    "spray machine": "распылительная установка",
    "water spray": "распылительная установка",
}


def has_chinese(text):
    return bool(CHINESE_FRAGMENT_RE.search(str(text)))


def _apply_mapping(text, mapping):
    value = str(text)
    for source in sorted(mapping, key=len, reverse=True):
        value = value.replace(source, mapping[source])
    return value


def normalize_punctuation(text):
    value = str(text).translate(FULLWIDTH_PUNCT_MAP)
    value = value.replace("_", " ")
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\(\s+", "(", value)
    value = re.sub(r"\s+\)", ")", value)
    value = re.sub(r"\s*([:;,])\s*", r"\1 ", value)
    value = re.sub(r"\s*\.\s*", ". ", value)
    value = re.sub(r"\s*\+\s*", " + ", value)
    value = re.sub(r"(?<=\d)([А-Яа-яЁёA-Za-z])", r" \1", value)
    value = re.sub(r"(?<=\d)(\()", r" \1", value)
    value = re.sub(r"(?<=[А-Яа-яЁё])(?=\d)", " ", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\s+([,.;:)])", r"\1", value)
    value = value.strip(" -_")
    return value.strip()


def _build_residual_dictionary(section=None):
    merged = {}
    merged.update(PHRASE_REPLACEMENTS)
    merged.update(TOKEN_REPLACEMENTS)
    merged.update(MIXED_OUTPUT_REPLACEMENTS)
    section_name = str(section or "").strip()
    if section_name:
        merged.update(build_section_term_map(section_name))
    return merged


def replace_known_terms(text, section=None):
    value = normalize_punctuation(text)
    mapping = _build_residual_dictionary(section)
    value = NUMBER_CN_UNIT_RE.sub(lambda match: f"{match.group(1)} {mapping.get(match.group(2), match.group(2))}", value)
    value = _apply_mapping(value, mapping)
    return normalize_punctuation(value)


def strip_prompt_leak(text):
    value = str(text).strip()

    if not value:
        return value

    if re.match(r"^\s*(?:rules?|правила)\s*:", value, flags=re.IGNORECASE):
        value = PROMPT_LEAK_RE.sub("", value)

    value = LEADING_RULE_LINE_RE.sub("", value).strip()
    value = LEADING_BULLET_RE.sub("", value).strip()
    value = re.sub(r"^\s*(?:text|текст)\s*:\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _meaningful_token_count(text):
    return len(MEANINGFUL_TOKEN_RE.findall(str(text)))


def _fragment_from_dict(fragment, mapping):
    value = _apply_mapping(fragment, mapping)
    return value


def replace_residual_chinese(text, section=None):
    mapping = _build_residual_dictionary(section)
    value = normalize_punctuation(text)
    value = NUMBER_CN_UNIT_RE.sub(lambda match: f"{match.group(1)} {mapping.get(match.group(2), match.group(2))}", value)

    def repl(match):
        fragment = match.group(0)
        translated = _fragment_from_dict(fragment, mapping)
        return translated

    value = CHINESE_FRAGMENT_RE.sub(repl, value)
    return normalize_punctuation(value)


def _source_has_structural_density(source_text):
    source_text = str(source_text)
    return (
        source_text.count("，") + source_text.count(",") >= 2
        or "（" in source_text
        or "(" in source_text
        or bool(re.search(r"\d[\u4e00-\u9fff]", source_text))
        or "：" in source_text
        or ":" in source_text
    )


def _candidate_is_thin(source_text, candidate_text):
    source_text = str(source_text).strip()
    candidate_text = str(candidate_text).strip()
    if not candidate_text:
        return True
    if PUNCT_ONLY_RE.match(candidate_text):
        return True
    if _source_has_structural_density(source_text) and _meaningful_token_count(candidate_text) < 3:
        return True
    return False


def finalize_translation(source_text, translated_text, section=None):
    source_text = normalize_punctuation(str(source_text).strip())
    section_name = section or detect_section_for_text(source_text)
    value = strip_prompt_leak(str(translated_text).strip())
    value = normalize_punctuation(value)
    value = replace_known_terms(value, section_name)
    value = replace_residual_chinese(value, section_name)

    if _candidate_is_thin(source_text, value):
        rebuilt = translate_structured_cn_text(source_text, section_name)
        rebuilt = replace_known_terms(rebuilt, section_name)
        rebuilt = replace_residual_chinese(rebuilt, section_name)
        if _meaningful_token_count(rebuilt) > _meaningful_token_count(value):
            value = rebuilt

    value = normalize_punctuation(value)

    qc_flags = []
    untranslated = has_chinese(value)
    if untranslated:
        if re.fullmatch(r"[\u4e00-\u9fff]", value):
            qc_flags.append("single_char_chinese")
        if re.search(r"\d\s*[\u4e00-\u9fff]", value):
            qc_flags.append("number_prefix_chinese")
        if len(CHINESE_FRAGMENT_RE.findall(value)) >= 2:
            qc_flags.append("multiple_chinese_fragments")
        qc_flags.append("needs_manual_review")

    return value, untranslated, qc_flags


def cleanup_translation(text, section=None):
    value, _, _ = finalize_translation("", text, section)
    return value
