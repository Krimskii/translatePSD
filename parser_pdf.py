import pandas as pd

from pdf_utils import extract_pdf_blocks

def parse_pdf(file):
    blocks = extract_pdf_blocks(file)
    texts = [block.text for block in blocks]
    return pd.DataFrame({"text": texts})
