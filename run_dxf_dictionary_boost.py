import argparse
import tempfile
from pathlib import Path

import ezdxf
import pandas as pd

from dictionary_booster import boost_dictionary_with_deepseek, extract_booster_candidates
from parser_dxf_block import extract_texts


def _load_dxf_dataframe(path):
    doc = ezdxf.readfile(path)
    return pd.DataFrame(extract_texts(doc), columns=["handle", "text"])


def main():
    parser = argparse.ArgumentParser(description="Build a DeepSeek-assisted booster dictionary for a DXF file.")
    parser.add_argument("dxf", help="Path to DXF file")
    parser.add_argument("--preview", action="store_true", help="Only show dictionary candidates; do not call DeepSeek")
    parser.add_argument("--candidate-limit", type=int, default=120)
    parser.add_argument("--deepseek-limit", type=int, default=80)
    parser.add_argument("--terms-output", default="", help="Optional Excel output for suggested terms")
    args = parser.parse_args()

    df = _load_dxf_dataframe(args.dxf)
    candidates = extract_booster_candidates(df, limit=args.candidate_limit)
    print(f"DXF rows for translation: {len(df)}")
    print(f"Dictionary candidates: {len(candidates)}")

    if args.preview:
        print(candidates.head(40).to_string(index=False))
        return

    result = boost_dictionary_with_deepseek(
        df,
        candidate_limit=args.candidate_limit,
        deepseek_limit=args.deepseek_limit,
    )
    summary = result["summary"]
    print(f"Booster dictionary updated: added={summary['added']} updated={summary['updated']} path={summary['path']}")

    if args.terms_output:
        output = Path(args.terms_output)
    else:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".deepseek_terms.xlsx")
        tmp.close()
        output = Path(tmp.name)
    result["terms"].to_excel(output, index=False)
    print(f"Suggested terms written to {output}")


if __name__ == "__main__":
    main()
