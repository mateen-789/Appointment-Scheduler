from datetime import date
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from PIL import UnidentifiedImageError
from pydantic import BaseModel

from entities import DEPARTMENT_MAP, extract_entities
from normalization import normalize
from ocr import extract_text_from_image

app = FastAPI(title="Appointment Scheduler Assistant")

# Below this OCR confidence we don't trust the text enough to continue
MIN_OCR_CONFIDENCE = 0.5


def needs_clarification(message: str) -> dict:
    return {"status": "needs_clarification", "message": message}


async def get_raw_text(text: Optional[str], image: Optional[UploadFile]) -> dict:
    """Stage 1: turn typed text or an uploaded image into raw_text + confidence."""
    if text and image:
        raise HTTPException(status_code=400, detail="Provide either 'text' or 'image', not both.")

    if text and text.strip():
        return {"raw_text": text.strip(), "confidence": 1.0}

    if image:
        contents = await image.read()
        try:
            result = extract_text_from_image(contents)
        except UnidentifiedImageError:
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")
        if not result["raw_text"]:
            raise HTTPException(status_code=422, detail="No readable text found in the image.")
        return result

    raise HTTPException(status_code=400, detail="Provide either 'text' or an 'image'.")


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Server is running"}


# ---------- Individual stages (useful for testing each step) ----------

@app.post("/extract-text")
async def extract_text(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
):
    return await get_raw_text(text, image)


class TextInput(BaseModel):
    raw_text: str


@app.post("/extract-entities")
def extract_entities_endpoint(payload: TextInput):
    if not payload.raw_text.strip():
        raise HTTPException(status_code=400, detail="'raw_text' must not be empty.")
    return extract_entities(payload.raw_text)


class NormalizeInput(BaseModel):
    date_phrase: Optional[str] = None
    time_phrase: Optional[str] = None
    reference_date: Optional[date] = None  # pretend "today" is this date (for testing)


@app.post("/normalize")
def normalize_endpoint(payload: NormalizeInput):
    return normalize(payload.date_phrase, payload.time_phrase, payload.reference_date)


# ---------- Full pipeline ----------

@app.post("/schedule")
async def schedule(
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    reference_date: Optional[date] = None,  # optional query param, for reproducible testing
):
    # Stage 1: OCR / text extraction
    extracted = await get_raw_text(text, image)
    if extracted["confidence"] < MIN_OCR_CONFIDENCE:
        return needs_clarification("Text could not be read reliably. Please retake the image or type the request.")

    # Stage 2: entity extraction
    entities = extract_entities(extracted["raw_text"])["entities"]
    if not entities["department"]:
        return needs_clarification("Missing or ambiguous department: could not tell which department to book.")

    # Stage 3: normalization (also handles missing/invalid/past date and time)
    result = normalize(entities["date_phrase"], entities["time_phrase"], reference_date)
    if result.get("status") == "needs_clarification":
        return result

    # Stage 4: final appointment JSON
    return {
        "appointment": {
            "department": DEPARTMENT_MAP[entities["department"]],
            **result["normalized"],  # adds date, time, tz
        },
        "status": "ok",
    }