import pandas as pd

def load_dictionary():

    df = pd.read_excel("dictionary/dictionary.xlsx")

    return dict(zip(df["CN"], df["RU"]))


def apply_dictionary(text, dictionary):

    for k,v in dictionary.items():
        text = str(text).replace(k,v)

    return text