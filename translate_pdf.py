import pdfplumber
import pandas as pd

from translator_hybrid import translate_df


def translate_pdf(src, dst):

    texts = []

    with pdfplumber.open(src) as pdf:

        for page in pdf.pages:

            t = page.extract_text()

            if t:
                texts.extend(t.split("\n"))

    df = pd.DataFrame({"text": texts})

    df = translate_df(df)

    with open(dst + ".txt", "w", encoding="utf8") as f:

        for t in df["translated"]:
            f.write(t + "\n")