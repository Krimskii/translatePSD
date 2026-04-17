import ezdxf

def write_translated_dxf(input_path, output_path, df):

    doc = ezdxf.readfile(input_path)

    msp = doc.modelspace()

    i = 0

    for entity in msp:

        if entity.dxftype() == "TEXT":

            if i < len(df):

                entity.dxf.text = str(df["normalized"].iloc[i])

                i += 1

        elif entity.dxftype() == "MTEXT":

            if i < len(df):

                entity.text = str(df["normalized"].iloc[i])

                i += 1

    doc.saveas(output_path)