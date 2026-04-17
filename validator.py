import re

import pandas as pd

from normative_dictionary import load_normative_dictionary
from validator_sections import detect_section
from validator_snrk import check_rules


CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


def _check_normative_dictionary(section, source_text, translated_text):
    issues = []
    dictionaries = load_normative_dictionary()
    approved = {}

    for source, target in dictionaries.get("ALL", {}).items():
        approved[source] = target

    for source, target in dictionaries.get(section, {}).items():
        approved[source] = target

    translated_lower = translated_text.lower()

    for source, target in sorted(approved.items(), key=lambda item: len(item[0]), reverse=True):
        source = str(source).strip()
        target = str(target).strip()

        if not source or not target:
            continue

        if source not in source_text:
            continue

        if target.lower() not in translated_lower:
            issues.append(f"Термин '{source}' должен быть приведен как '{target}'")

    return issues


def validate_df(df):
    report = []

    for index, row in df.iterrows():
        source_text = str(row.get("text", ""))
        text = str(row.get("normalized", row.get("translated", source_text)))
        section = detect_section(source_text)
        issues = []

        if not text.strip():
            issues.append("Пустой результат перевода")

        if CHINESE_RE.search(text):
            issues.append("Остались китайские символы")

        issues.extend(_check_normative_dictionary(section, source_text, text))
        issues.extend(check_rules(section, text))

        report.append(
            {
                "row": index,
                "section": section,
                "text": text,
                "status": "OK" if not issues else "WARN",
                "issues": "; ".join(issues),
            }
        )

    return pd.DataFrame(report)
