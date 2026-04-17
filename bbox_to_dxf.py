def insert_texts_from_ocr(doc, boxes, translated):
    """Insert OCR results back into modelspace as MTEXT notes."""
    msp = doc.modelspace()

    for box, text in zip(boxes, translated):
        bbox = box.get("bbox") or []
        if not bbox or len(bbox) < 1:
            continue

        point = bbox[0]
        if not isinstance(point, (list, tuple)) or len(point) < 2:
            continue

        x, y = float(point[0]), float(point[1])
        value = str(text).strip()
        if not value:
            continue

        msp.add_mtext(
            value,
            dxfattribs={
                "char_height": 2.5,
                "insert": (x, y),
            },
        )
