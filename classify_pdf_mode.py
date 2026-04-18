import argparse
import json

from pdf_utils import classify_pdf_mode


def main():
    parser = argparse.ArgumentParser(description="Classify PDF pages as text / hybrid / scanned.")
    parser.add_argument("source", help="Path to PDF")
    args = parser.parse_args()

    info = classify_pdf_mode(args.source)
    print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
