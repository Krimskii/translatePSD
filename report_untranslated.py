import argparse
import re

import pandas as pd


CHINESE_RE = re.compile(r"[\u4e00-\u9fff]")


def read_table(path):
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def main():
    parser = argparse.ArgumentParser(description="Report untranslated Chinese fragments from translated outputs.")
    parser.add_argument("source", help="Input Excel/CSV file")
    parser.add_argument("--output", help="Optional output Excel/CSV report")
    args = parser.parse_args()

    frame = read_table(args.source)
    translated_col = "normalized" if "normalized" in frame.columns else "translated"
    if translated_col not in frame.columns:
        raise SystemExit("Expected 'translated' or 'normalized' column in input file.")

    report = frame[frame[translated_col].astype(str).str.contains(CHINESE_RE, na=False)].copy()
    report["report_column"] = translated_col
    print(f"Untranslated rows: {len(report)}")

    if args.output:
        if args.output.lower().endswith(".csv"):
            report.to_csv(args.output, index=False, encoding="utf-8-sig")
        else:
            report.to_excel(args.output, index=False)
        print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
