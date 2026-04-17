import argparse

from merge_pipeline import full_translate_dxf


def main():
    parser = argparse.ArgumentParser(description="Translate DXF with OCR fallback.")
    parser.add_argument("src", help="Path to source DXF file")
    parser.add_argument("dst", help="Path to translated DXF file")
    parser.add_argument("--tmp-dir", default="tmp", help="Directory for temporary artifacts")
    args = parser.parse_args()

    full_translate_dxf(args.src, args.dst, tmp_dir=args.tmp_dir)


if __name__ == "__main__":
    main()
