import os

import cv2


os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_OCR = None


def _get_ocr():
    global _OCR
    if _OCR is None:
        from paddleocr import PaddleOCR

        _OCR = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _OCR


def _bbox_bounds(bbox):
    xs = [float(point[0]) for point in bbox]
    ys = [float(point[1]) for point in bbox]
    return min(xs), min(ys), max(xs), max(ys)


def _merge_lines(lines):
    if not lines:
        return []

    ordered = sorted(lines, key=lambda item: (item["bounds"][1], item["bounds"][0]))
    merged = []

    for item in ordered:
        if not merged:
            merged.append(item)
            continue

        prev = merged[-1]
        px0, py0, px1, py1 = prev["bounds"]
        x0, y0, x1, y1 = item["bounds"]

        prev_height = max(py1 - py0, 1.0)
        same_row = abs(y0 - py0) <= prev_height * 0.55
        near_horizontally = x0 - px1 <= prev_height * 2.5

        if same_row and near_horizontally:
            prev["text"] = f'{prev["text"]} {item["text"]}'.strip()
            prev["score"] = min(prev["score"], item["score"])
            prev["bounds"] = (min(px0, x0), min(py0, y0), max(px1, x1), max(py1, y1))
            prev["bbox"] = [
                [prev["bounds"][0], prev["bounds"][1]],
                [prev["bounds"][2], prev["bounds"][1]],
                [prev["bounds"][2], prev["bounds"][3]],
                [prev["bounds"][0], prev["bounds"][3]],
            ]
        else:
            merged.append(item)

    return merged


def detect_text_boxes(img_path):
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Image not found or unreadable: {img_path}")

    result = _get_ocr().ocr(img, cls=True)
    if not result or not result[0]:
        return []

    lines = []
    for line in result[0]:
        bbox = line[0]
        text = str(line[1][0]).strip()
        score = float(line[1][1])

        if score < 0.45 or not text:
            continue

        bounds = _bbox_bounds(bbox)
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]

        if width < 6 or height < 6:
            continue

        lines.append({"bbox": bbox, "bounds": bounds, "text": text, "score": score})

    merged = _merge_lines(lines)
    for item in merged:
        item.pop("bounds", None)

    return merged
