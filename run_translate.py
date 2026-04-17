import argparse

from translate_project import translate_project


def main():
    parser = argparse.ArgumentParser(description="Translate a whole project directory.")
    parser.add_argument("src", help="Source project directory")
    parser.add_argument("dst", help="Destination project directory")
    args = parser.parse_args()

    translate_project(args.src, args.dst)


if __name__ == "__main__":
    main()
