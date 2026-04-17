import os
os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
from paddleocr import PaddleOCR
import cv2

ocr = PaddleOCR(use_angle_cls=True, lang='ch')


def detect_text_boxes(img_path):
    img = cv2.imread(img_path)
    result = ocr.ocr(img, cls=True)

    boxes = []
    for line in result[0]:
        bbox = line[0]  # 4 точки
        text = line[1][0]
        score = line[1][1]

        if score < 0.6:
            continue

        boxes.append({
            "bbox": bbox,
            "text": text
        })

    return boxes