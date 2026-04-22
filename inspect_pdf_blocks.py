import argparse

from pdf_utils import build_pdf_qc_report, classify_pdf_mode


def main():
    parser = argparse.ArgumentParser(description="Inspect PDF text/OCR blocks.")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--output", default="pdf_blocks_report.xlsx", help="Output XLSX report path")
    args = parser.parse_args()

    mode_info = classify_pdf_mode(args.pdf)
    report = build_pdf_qc_report(args.pdf)
    report.to_excel(args.output, index=False)

    print("PDF mode:", mode_info["mode"])
    print("Pages:", len(mode_info["page_stats"]))
    print("Blocks:", len(report))
    if not report.empty:
        print("Sources:")
        print(report["source"].value_counts().to_string())
        print("Blocks with Chinese:", int(report["has_chinese"].sum()))
    print("Report:", args.output)


if __name__ == "__main__":
    main()
