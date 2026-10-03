import io

import pytesseract
from PIL import Image


def extract_text_from_image(image_bytes: bytes) -> dict:
    """Run OCR on raw image bytes and return the text with an average confidence (0-1)."""
    image = Image.open(io.BytesIO(image_bytes))

    # image_to_data gives per-word text and confidence scores
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    words = []
    confidences = []
    for word, conf in zip(data["text"], data["conf"]):
        # Tesseract uses conf = -1 for non-word entries (blank boxes), so skip those
        if word.strip() and float(conf) >= 0:
            words.append(word.strip())
            confidences.append(float(conf))

    raw_text = " ".join(words)
    confidence = round(sum(confidences) / len(confidences) / 100, 2) if confidences else 0.0

    return {"raw_text": raw_text, "confidence": confidence}