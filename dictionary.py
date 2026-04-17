from auto_dictionary import load_dict


def load_dictionary():
    df = load_dict()
    return dict(zip(df["CN"], df["RU"]))


def apply_dictionary(text, dictionary):
    for key, value in dictionary.items():
        text = str(text).replace(key, value)

    return text
