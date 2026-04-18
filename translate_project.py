import logging
import os
import shutil
from pathlib import Path

from output_names import build_ru_name
from translate_docx import translate_docx
from translate_dxf import translate_dxf
from translate_excel import translate_excel
from translate_pdf import translate_pdf


LOGGER = logging.getLogger(__name__)


def translate_project(root, out):
    summary = []

    for path, _dirs, files in os.walk(root):
        rel = os.path.relpath(path, root)
        out_dir = os.path.join(out, rel)
        os.makedirs(out_dir, exist_ok=True)

        for file_name in files:
            src = os.path.join(path, file_name)
            ext = file_name.lower()
            dst_name = build_ru_name(file_name, output_ext=".xlsx" if ext.endswith((".xls", ".xlsx")) else None)
            dst = os.path.join(out_dir, dst_name)
            LOGGER.info("translate: %s", src)

            try:
                if ext.endswith(".pdf"):
                    translate_pdf(src, dst)
                    status = "translated"
                elif ext.endswith(".docx"):
                    translate_docx(src, dst)
                    status = "translated"
                elif ext.endswith((".xlsx", ".xls")):
                    translate_excel(src, dst)
                    status = "translated"
                elif ext.endswith(".dxf"):
                    translate_dxf(src, dst)
                    status = "translated"
                else:
                    shutil.copy2(src, dst)
                    status = "copied"
            except Exception as exc:
                LOGGER.exception("Failed to process %s", src)
                shutil.copy2(src, dst)
                status = f"error:{exc}"

            summary.append({"source": src, "output": dst, "status": status})

    return summary
