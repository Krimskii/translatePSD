import argparse
from pathlib import Path

import pandas as pd

from deepseek_consult import run_deepseek_audit


def _read_table(path):
    suffix = Path(path).suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError("Supported inputs: .xlsx, .xls, .csv")


def main():
    parser = argparse.ArgumentParser(description="Ask DeepSeek to audit a translation report/table.")
    parser.add_argument("input", help="Translated Excel/CSV table with text/translated/qc columns")
    parser.add_argument("--output", default="", help="Markdown output path")
    parser.add_argument("--focus", default="", help="Audit focus/question")
    args = parser.parse_args()

    df = _read_table(args.input)
    result = run_deepseek_audit(df, file_name=Path(args.input).name, user_focus=args.focus)

    output = Path(args.output) if args.output else Path(args.input).with_suffix(".deepseek_audit.md")
    output.write_text(result["answer"], encoding="utf-8-sig")
    prompt_output = output.with_suffix(".prompt.md")
    prompt_output.write_text(result["prompt"], encoding="utf-8-sig")
    print(f"Audit written to {output}")
    print(f"Prompt written to {prompt_output}")


if __name__ == "__main__":
    main()
