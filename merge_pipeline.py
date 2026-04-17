import os

import ezdxf


def full_translate_dxf(src, dst, tmp_dir="tmp"):
    from bbox_to_dxf import insert_texts_from_ocr
    from ocr_detect import detect_text_boxes
    from render_dxf_to_png import render_dxf_to_png
    from translate_dxf import translate_dxf
    from translate_ocr import translate_ocr_texts

    os.makedirs(tmp_dir, exist_ok=True)

    print("STEP 1: base DXF translate")
    tmp_dxf = os.path.join(tmp_dir, "base.dxf")
    translate_dxf(src, tmp_dxf)

    print("STEP 2: render")
    img_path = os.path.join(tmp_dir, "render.png")
    render_dxf_to_png(tmp_dxf, img_path, dpi=400)

    print("STEP 3: OCR detect")
    boxes = detect_text_boxes(img_path)
    print("found OCR:", len(boxes))

    texts = [b["text"] for b in boxes]
    if not texts:
        doc = ezdxf.readfile(tmp_dxf)
        doc.saveas(dst)
        print("DONE:", dst)
        return

    print("STEP 4: translate OCR")
    translated = translate_ocr_texts(texts)

    print("STEP 5: inject back")
    doc = ezdxf.readfile(tmp_dxf)
    insert_texts_from_ocr(doc, boxes, translated)
    doc.saveas(dst)

    print("DONE:", dst)
