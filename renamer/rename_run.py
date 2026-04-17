import argparse

from rename_tree_batch import translate_tree


def main():
    parser = argparse.ArgumentParser(description="Translate file and folder names in a tree.")
    parser.add_argument("root", help="Root directory to rename")
    args = parser.parse_args()

    translate_tree(args.root)


if __name__ == "__main__":
    main()
