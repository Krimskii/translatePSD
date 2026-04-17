import os
import shutil

from translate_pdf import translate_pdf
from translate_docx import translate_docx
from translate_excel import translate_excel
from translate_dxf import translate_dxf


def translate_project(root, out):

    for path, dirs, files in os.walk(root):

        rel = os.path.relpath(path, root)
        out_dir = os.path.join(out, rel)

        os.makedirs(out_dir, exist_ok=True)

        for file in files:

            src = os.path.join(path, file)
            dst = os.path.join(out_dir, file)

            print("translate:", file)

            ext = file.lower()

            try:

                if ext.endswith(".pdf"):
                    translate_pdf(src, dst)

                elif ext.endswith(".docx"):
                    translate_docx(src, dst)

                elif ext.endswith(".xlsx"):
                    translate_excel(src, dst)

                elif ext.endswith(".dxf"):
                    translate_dxf(src, dst)

                else:
                    shutil.copy2(src, dst)

            except Exception as e:
                print("ERROR:", file, e)
                shutil.copy2(src, dst)