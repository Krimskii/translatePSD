import shutil

import pandas as pd
import pdfplumber

from translator_hybrid import translate_df


def translate_pdf(src, dst):
    texts = []

    with pdfplumber.open(src) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                texts.extend(page_text.split("\n"))

    df = pd.DataFrame({"text": texts})
    df = translate_df(df)

    shutil.copy2(src, dst)
    sidecar_path = f"{dst}.translated.txt"

    with open(sidecar_path, "w", encoding="utf-8") as file:
        for text in df["translated"]:
            file.write(f"{text}\n")

    return sidecar_path
