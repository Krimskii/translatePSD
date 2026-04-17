import os


def build_ru_name(filename, output_ext=None):
    base_name = os.path.basename(str(filename))
    stem, ext = os.path.splitext(base_name)
    final_ext = output_ext or ext
    return f"{stem}_RU{final_ext}"


def build_ru_path(path, output_ext=None):
    directory = os.path.dirname(str(path))
    return os.path.join(directory, build_ru_name(path, output_ext=output_ext))
