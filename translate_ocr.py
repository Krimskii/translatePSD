import pandas as pd
from translator_hybrid import translate_df


def translate_ocr_texts(texts):
    df = pd.DataFrame({"text": texts})
    df = translate_df(df)
    return df["translated"].tolist()