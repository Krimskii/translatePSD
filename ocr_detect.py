import os

import cv2


os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_OCR = None


def _get_ocr():
    global _OCR
    if _OCR is None:
        from paddleocr import PaddleOCR

        _OCR = PaddleOCR(use_angle_cls=True, lang="ch")
    return _OCR


def detect_text_boxes(img_path):
    img = cv2.imread(img_path)
    if img is None:
        raise FileNotFoundError(f"Image not found or unreadable: {img_path}")

    result = _get_ocr().ocr(img, cls=True)
    if not result or not result[0]:
        return []

    boxes = []
    for line in result[0]:
        bbox = line[0]
        text = line[1][0]
        score = line[1][1]

        if score < 0.6:
            continue

        boxes.append({"bbox": bbox, "text": text, "score": score})

    return boxes
