import re

import pandas as pd


LLM_SOURCE_RE = re.compile(r"^(?:ollama|deepseek|fallback)")
FAST_SOURCE_RE = re.compile(r"^(?:passthrough|memory|structured_dict|section_dict)")


def split_qc_flags(value):
    return [flag.strip() for flag in str(value or "").split(",") if flag.strip()]


def build_translation_metrics(df):
    if df is None or df.empty:
        return {
            "rows": 0,
            "fast_rows": 0,
            "llm_rows": 0,
            "duplicate_rows": 0,
            "memory_rows": 0,
            "dictionary_rows": 0,
            "passthrough_rows": 0,
            "untranslated_chinese_rows": 0,
            "qc_flagged_rows": 0,
            "qc_flags": "",
        }

    source = df.get("translation_source", pd.Series([""] * len(df), index=df.index)).astype(str)
    qc = df.get("qc_flags", pd.Series([""] * len(df), index=df.index)).astype(str)
    untranslated = df.get("untranslated_chinese", pd.Series([False] * len(df), index=df.index)).fillna(False).astype(bool)

    all_flags = []
    for value in qc.tolist():
        all_flags.extend(split_qc_flags(value))

    return {
        "rows": int(len(df)),
        "fast_rows": int(source.str.match(FAST_SOURCE_RE).sum()),
        "llm_rows": int(source.str.match(LLM_SOURCE_RE).sum()),
        "duplicate_rows": int(source.str.contains("duplicate", regex=False).sum()),
        "memory_rows": int(source.str.startswith("memory").sum()),
        "dictionary_rows": int(source.str.match(r"^(?:structured_dict|section_dict)").sum()),
        "passthrough_rows": int(source.str.startswith("passthrough").sum()),
        "untranslated_chinese_rows": int(untranslated.sum()),
        "qc_flagged_rows": int(qc.str.strip().ne("").sum()),
        "qc_flags": ", ".join(sorted(set(all_flags))),
    }
