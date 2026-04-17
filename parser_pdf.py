import pdfplumber
import pandas as pd

def parse_pdf(file):
    texts = []

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            txt = page.extract_text()
            if txt:
                lines = txt.split("\n")
                texts.extend(lines)

    return pd.DataFrame({"text": texts})
