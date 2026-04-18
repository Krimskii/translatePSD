def detect_section(text):
    text = str(text)

    if any(token in text for token in ["工艺", "流程", "原料", "熔铸", "挤压", "时效", "表面处理", "包装", "能耗", "能源"]):
        return "ТХ"

    if "电气" in text:
        return "ЭОМ"

    if "消防" in text:
        return "ПБ"

    if "给排水" in text:
        return "ВК"

    if "暖通" in text or "通风" in text:
        return "ОВ"

    if "结构" in text:
        return "КЖ"

    if "建筑" in text:
        return "АР"

    return "UNKNOWN"
