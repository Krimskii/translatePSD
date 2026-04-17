import os
import shutil

from dwg_utils import convert_dwg_to_dxf
from translate_docx import translate_docx
from translate_dxf import translate_dxf
from translate_excel import translate_excel
from translate_pdf import translate_pdf


def translate_project(root, out):
    for path, _dirs, files in os.walk(root):
        rel = os.path.relpath(path, root)
        out_dir = os.path.join(out, rel)
        os.makedirs(out_dir, exist_ok=True)

        for file_name in files:
            src = os.path.join(path, file_name)
            dst = os.path.join(out_dir, file_name)
            ext = file_name.lower()

            print("translate:", file_name)

            try:
                if ext.endswith(".pdf"):
                    translate_pdf(src, dst)
                elif ext.endswith(".docx"):
                    translate_docx(src, dst)
                elif ext.endswith(".xlsx") or ext.endswith(".xls"):
                    translate_excel(src, dst)
                elif ext.endswith(".dwg"):
                    dst = os.path.splitext(dst)[0] + ".dxf"
                    convert_dwg_to_dxf(src, dst)
                elif ext.endswith(".dxf"):
                    translate_dxf(src, dst)
                else:
                    shutil.copy2(src, dst)
            except Exception as e:
                print("ERROR:", file_name, e)
                shutil.copy2(src, dst)
