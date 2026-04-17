import re

import pandas as pd

from validator_sections import detect_section
from validator_snrk import check_rules


CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


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
