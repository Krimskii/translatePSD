import argparse

from translate_dxf import translate_dxf


def main():
    parser = argparse.ArgumentParser(description="Translate DXF text entities.")
    parser.add_argument("src", help="Path to source DXF file")
    parser.add_argument("dst", help="Path to translated DXF file")
    args = parser.parse_args()

    translate_dxf(args.src, args.dst)


if __name__ == "__main__":
    main()
