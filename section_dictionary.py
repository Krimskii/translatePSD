from normative_dictionary import apply_normative_terms, load_normative_dictionary
from validator_sections import detect_section


SECTION_TERMS = {
    "ОВ": {
        "通风": "вентиляция",
        "排风": "вытяжка",
        "送风": "приток",
        "新风": "свежий воздух",
        "风管": "воздуховод",
        "风口": "воздухораспределитель",
        "排风口": "вытяжной воздухораспределитель",
        "送风口": "приточный воздухораспределитель",
        "风机": "вентилятор",
        "空调": "кондиционирование",
        "暖通": "отопление и вентиляция",
        "局部排风罩": "местный вытяжной зонт",
        "热回收": "утилизация тепла",
    },
    "ВК": {
        "给排水": "водоснабжение и канализация",
        "排水沟": "водоотводный лоток",
        "污水沟": "лоток сточных вод",
        "污水": "сточные воды",
        "雨水": "дождевые воды",
        "方井": "квадратный колодец",
        "圆井": "круглый колодец",
        "井": "колодец",
        "管道": "трубопровод",
        "水泵": "насос",
        "阀门": "задвижка",
        "喷雾机水": "вода от распылительной установки",
    },
    "ЭОМ": {
        "电气": "электроснабжение",
        "配电箱": "щит распределительный",
        "桥架": "кабельный лоток",
        "电缆": "кабель",
        "照明": "освещение",
        "接地": "заземление",
    },
    "КЖ": {
        "结构": "конструкции",
        "钢构柱": "стальная колонна",
        "柱面": "грань колонны",
        "基础": "фундамент",
        "梁": "балка",
        "板": "плита",
        "牛腿": "консоль",
        "行车牛腿": "подкрановая консоль",
        "钢筋": "арматура",
        "混凝土": "бетон",
    },
    "АР": {
        "建筑": "архитектурные решения",
        "车间门": "дверь цеха",
        "门": "дверь",
        "窗": "окно",
        "屋面": "кровля",
        "总平面": "генеральный план",
        "办公楼": "административно-бытовой корпус",
    },
    "UNKNOWN": {},
}


def detect_section_for_text(text):
    text = str(text)
    section = detect_section(text)
    return section if section in SECTION_TERMS else "UNKNOWN"


def apply_section_terms(text, section=None):
    value = str(text)
    section_name = section or detect_section_for_text(value)
    merged_terms = dict(SECTION_TERMS.get(section_name, {}))

    for source, target in load_normative_dictionary().get("ALL", {}).items():
        merged_terms[source] = target

    for source, target in load_normative_dictionary().get(section_name, {}).items():
        merged_terms[source] = target

    for source, target in sorted(merged_terms.items(), key=lambda item: len(item[0]), reverse=True):
        value = value.replace(source, target)

    return apply_normative_terms(value, section_name)
