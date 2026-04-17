import re

def fix_chinese(text):

    t = str(text)

    # если остались китайские символы
    if re.search(r'[\u4e00-\u9fff]', t):

        t = t.replace("镀锌管", "оцинкованная труба")
        t = t.replace("井", "колодец")
        t = t.replace("泵", "насос")
        t = t.replace("管", "труба")
        t = t.replace("阀", "клапан")

    return t