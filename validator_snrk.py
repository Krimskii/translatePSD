def check_rules(section, text):
    issues = []

    if section == "ПБ":
        if "喷粉" in text:
            issues.append("Требуется взрывозащита СП РК ПБ")

    if section == "ОВ":
        if " печь" in text.lower():
            issues.append("Проверить вытяжную вентиляцию СП РК ОВ")

    if section == "ЭОМ":
        if "shield" in text.lower():
            issues.append("Проверить ПУЭ РК")

    if section == "КЖ":
        if "steel" in text.lower():
            issues.append("СП РК КМ проверить нагрузки")

    return issues
