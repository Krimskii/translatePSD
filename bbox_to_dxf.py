def _pixel_to_world(x, y, render_meta):
    x_min, x_max = render_meta["xlim"]
    y_a, y_b = render_meta["ylim"]
    width, height = render_meta["image_size"]

    if width <= 0 or height <= 0:
        raise ValueError("Invalid render size for OCR back-projection")

    world_x = x_min + (x / width) * (x_max - x_min)
    top_y = max(y_a, y_b)
    bottom_y = min(y_a, y_b)
    world_y = top_y - (y / height) * (top_y - bottom_y)

    return world_x, world_y


def _bbox_geometry(bbox):
    xs = [float(point[0]) for point in bbox]
    ys = [float(point[1]) for point in bbox]
    return min(xs), min(ys), max(xs), max(ys)


def insert_texts_from_ocr(doc, boxes, translated, render_meta):
    """Insert OCR results back into modelspace as MTEXT in DXF coordinates."""
    msp = doc.modelspace()

    for box, text in zip(boxes, translated):
        bbox = box.get("bbox") or []
        value = str(text).strip()

        if len(bbox) < 4 or not value:
            continue

        x0, y0, x1, y1 = _bbox_geometry(bbox)
        insert_x, insert_y = _pixel_to_world(x0, y0, render_meta)
        right_x, _ = _pixel_to_world(x1, y0, render_meta)
        _, bottom_y = _pixel_to_world(x0, y1, render_meta)

        width = max(abs(right_x - insert_x), 1.0)
        height = max(abs(insert_y - bottom_y), 1.0)
        char_height = max(height * 0.7, 1.8)

        mtext = msp.add_mtext(
            value,
            dxfattribs={
                "char_height": char_height,
                "insert": (insert_x, insert_y),
            },
        )
        mtext.dxf.width = width
        mtext.dxf.attachment_point = 1

        # Keep OCR overlays readable on top of the existing drawing.
        try:
            mtext.set_bg_color(7, scale=1.1)
        except AttributeError:
            pass
