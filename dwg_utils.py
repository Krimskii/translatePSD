import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _candidate_paths():
    program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
    program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

    return [
        "dwg2dxf",
        "ODAFileConverter",
        "ODAFileConverter.exe",
        "TeighaFileConverter",
        "TeighaFileConverter.exe",
        os.path.join(program_files, "ODA", "ODAFileConverter", "ODAFileConverter.exe"),
        os.path.join(program_files_x86, "ODA", "ODAFileConverter", "ODAFileConverter.exe"),
        os.path.join(program_files, "ODAFileConverter", "ODAFileConverter.exe"),
        os.path.join(program_files_x86, "ODAFileConverter", "ODAFileConverter.exe"),
        os.path.join(program_files, "Teigha File Converter", "TeighaFileConverter.exe"),
        os.path.join(program_files_x86, "Teigha File Converter", "TeighaFileConverter.exe"),
    ]


def find_dwg_converter():
    for candidate in _candidate_paths():
        resolved = shutil.which(candidate) or (candidate if os.path.exists(candidate) else None)
        if resolved:
            return resolved
    return None


def get_dwg_converter_help():
    return (
        "Для работы с DWG нужен внешний конвертер. "
        "Установите ODA File Converter или dwg2dxf, затем перезапустите приложение. "
        "Если конвертер уже установлен, добавьте его в PATH или установите в стандартную папку Program Files."
    )


def convert_dwg_to_dxf(src, dst):
    converter = find_dwg_converter()
    if not converter:
        raise RuntimeError(get_dwg_converter_help())

    converter_name = Path(converter).name.lower()

    if "dwg2dxf" in converter_name:
        subprocess.run([converter, src, "-o", dst], check=True, capture_output=True, text=True)
        return dst

    with tempfile.TemporaryDirectory() as input_dir, tempfile.TemporaryDirectory() as output_dir:
        src_path = Path(src)
        input_file = Path(input_dir) / src_path.name
        shutil.copy2(src, input_file)

        subprocess.run(
            [
                converter,
                input_dir,
                output_dir,
                "ACAD2018",
                "DXF",
                "0",
                "1",
                src_path.name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        produced = Path(output_dir) / f"{src_path.stem}.dxf"
        if not produced.exists():
            raise RuntimeError("Конвертер DWG завершился без выходного DXF файла.")

        shutil.copy2(produced, dst)

    return dst
