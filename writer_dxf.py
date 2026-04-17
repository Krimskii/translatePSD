import ezdxf

from dxf_utils import pick_output_text


def write_translated_dxf(input_path, output_path, df):
    doc = ezdxf.readfile(input_path)
    msp = doc.modelspace()
    index = 0

    for entity in msp:
        if entity.dxftype() not in {"TEXT", "MTEXT"}:
            continue
        if index >= len(df):
            break

        new_text = pick_output_text(df.iloc[index])
        index += 1

        if entity.dxftype() == "TEXT":
            entity.dxf.text = new_text
        else:
            entity.text = new_text

    doc.saveas(output_path)
