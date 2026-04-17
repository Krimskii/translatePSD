from auto_dictionary import load_dict

def apply_dictionary(text):

    dictionary = load_dict()

    for _,row in dictionary.iterrows():
        cn = str(row["CN"])
        ru = str(row["RU"])

        if ru and cn in text:
            text = text.replace(cn,ru)

    return text