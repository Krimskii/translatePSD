import argparse
import logging

import ezdxf
import pandas as pd

from parser_dxf_block import CHINESE_RE, extract_text_records


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def main():
    parser = argparse.ArgumentParser(description="Inspect DXF text entities.")
    parser.add_argument("source", help="Path to DXF file")
    parser.add_argument("--output", help="Optional Excel/CSV report path")
    args = parser.parse_args()

    doc = ezdxf.readfile(args.source)
    records = extract_text_records(doc)
    frame = pd.DataFrame(
        [
            {
                "handle": record.handle,
                "entity_type": record.entity_type,
                "layout_name": record.layout_name,
                "block_name": record.block_name,
                "layer": record.layer,
                "text": record.text,
                "has_chinese": bool(CHINESE_RE.search(record.text)),
            }
            for record in records
        ]
    )

    print(f"Total records: {len(frame)}")
    if not frame.empty:
        print(frame["entity_type"].value_counts().to_string())
        print(f"Records with Chinese: {int(frame['has_chinese'].sum())}")

    if args.output:
        if args.output.lower().endswith(".csv"):
            frame.to_csv(args.output, index=False, encoding="utf-8-sig")
        else:
            frame.to_excel(args.output, index=False)
        print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
