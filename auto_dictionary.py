import os

import pandas as pd


DICT_PATH = "dictionary/dictionary.xlsx"


def load_dict():
    os.makedirs(os.path.dirname(DICT_PATH), exist_ok=True)

    if not os.path.exists(DICT_PATH):
        df = pd.DataFrame(columns=["CN", "RU", "TYPE"])
        df.to_excel(DICT_PATH, index=False)

    return pd.read_excel(DICT_PATH)


def update_dictionary(df):
    dictionary = load_dict()
    existing = set(dictionary["CN"].astype(str))
    new_terms = [t for t in df["text"] if str(t) not in existing]

    if new_terms:
        new_df = pd.DataFrame({"CN": new_terms, "RU": "", "TYPE": ""})
        dictionary = pd.concat([dictionary, new_df], ignore_index=True)
        dictionary.drop_duplicates(inplace=True)
        dictionary.to_excel(DICT_PATH, index=False)

    return dictionary
