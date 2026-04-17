from cad_dictionary import CAD_DICT

def apply_cad_dict(text):

    t = str(text)

    for k,v in CAD_DICT.items():
        t = t.replace(k,v)

    return t