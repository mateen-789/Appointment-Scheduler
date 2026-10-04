# AI-Powered Appointment Scheduler Assistant

A backend service that turns natural-language appointment requests (typed text or
photos of notes) into structured scheduling data.

**Pipeline:** OCR / text extraction → entity extraction → normalization (Asia/Kolkata) → final appointment JSON, with guardrails that return `needs_clarification` when the input is missing or ambiguous.

## Architecture

```
text / image
     │
     ▼
[1] OCR (ocr.py)                 Tesseract; typed text passes through (confidence 1.0)
     │  low OCR confidence ───────────────► needs_clarification
     ▼
[2] Entity extraction (entities.py)   regex patterns + department keyword map
     │  missing department ───────────────► needs_clarification
     ▼
[3] Normalization (normalization.py)  phrases → ISO date/time in Asia/Kolkata
     │  missing / ambiguous / past date or time ► needs_clarification
     ▼
[4] Final appointment JSON (main.py)
```

| File | Responsibility |
|---|---|
| `main.py` | FastAPI app, endpoints, pipeline wiring, guardrails |
| `ocr.py` | Image → text + confidence using Tesseract |
| `entities.py` | Extracts date phrase, time phrase, department |
| `normalization.py` | Converts phrases to ISO date, 24h time, timezone |

## Setup

**Prerequisites:** Python 3.9+ and the [Tesseract OCR engine](https://github.com/tesseract-ocr/tesseract) installed and on your PATH
(Windows: UB Mannheim installer · macOS: `brew install tesseract` · Ubuntu: `sudo apt install tesseract-ocr`).

```bash
git clone https://github.com/mateen-789/Appointment-Scheduler
cd Appointment-Scheduler
python -m venv venv

# Windows PowerShell:  venv\Scripts\Activate.ps1
# macOS / Linux:       source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

The API runs at http://127.0.0.1:8000. Interactive docs: http://127.0.0.1:8000/docs

## API usage

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Health check |
| POST | `/extract-text` | Stage 1: text or image → `raw_text` + `confidence` |
| POST | `/extract-entities` | Stage 2: `raw_text` → entities |
| POST | `/normalize` | Stage 3: phrases → ISO date/time |
| POST | `/schedule` | Full pipeline → final appointment |

`/schedule` accepts an optional query parameter `reference_date` (YYYY-MM-DD) that fixes "today", so results are reproducible. Examples below use `2026-10-04`.
On Windows use `curl.exe` (plain `curl` is a PowerShell alias). On macOS/Linux, use `curl`.

### Full pipeline: typed text

```bash
curl.exe -X POST "http://127.0.0.1:8000/schedule?reference_date=2026-10-04" -F "text=Book dentist next Friday at 3pm"
```
```json
{"appointment": {"department": "Dentistry", "date": "2026-10-09", "time": "15:00", "tz": "Asia/Kolkata"}, "status": "ok"}
```

### Full pipeline: image

```bash
curl.exe -X POST "http://127.0.0.1:8000/schedule?reference_date=2026-10-04" -F "image=@sample.png"
```
Returns the same appointment JSON as above.

### Guardrail: ambiguous request

```bash
curl.exe -X POST "http://127.0.0.1:8000/schedule?reference_date=2026-10-04" -F "text=book appointment next friday"
```
```json
{"status": "needs_clarification", "message": "Missing or ambiguous department: could not tell which department to book."}
```

### Stage 1: OCR / text extraction

```bash
curl.exe -X POST http://127.0.0.1:8000/extract-text -F "text=Book dentist next Friday at 3pm"
```
```json
{"raw_text": "Book dentist next Friday at 3pm", "confidence": 1.0}
```

### Stage 2: entity extraction

```bash
curl.exe -X POST http://127.0.0.1:8000/extract-entities -H "Content-Type: application/json" -d "{\"raw_text\": \"book dentist nxt Friday @ 3 pm\"}"
```
```json
{"entities": {"date_phrase": "nxt Friday", "time_phrase": "3 pm", "department": "dentist"}, "entities_confidence": 0.85}
```
(On macOS/Linux you can write the body as `-d '{"raw_text": "book dentist nxt Friday @ 3 pm"}'`.)

### Stage 3: normalization

```bash
curl.exe -X POST http://127.0.0.1:8000/normalize -H "Content-Type: application/json" -d "{\"date_phrase\": \"nxt Friday\", \"time_phrase\": \"3 pm\", \"reference_date\": \"2026-10-04\"}"
```
```json
{"normalized": {"date": "2026-10-09", "time": "15:00", "tz": "Asia/Kolkata"}, "normalization_confidence": 0.9}
```

## Guardrails and error handling

- **Returns `needs_clarification` (HTTP 200)** when: OCR confidence is below 0.5, the department is missing, the date or time is missing, a phrase can't be parsed, or the date is in the past.
- **Returns HTTP 400** when no input is given, both text and image are given, or the uploaded file isn't a valid image.
- **Returns HTTP 422** when an image contains no readable text, or the JSON body doesn't match the schema.

## Design decisions and assumptions

- **Rule-based extraction** (regex + keyword map) was chosen for predictability, zero cost, and easy debugging. It handles shorthand such as "nxt" and "@".
- **"Next Friday"** is interpreted as the first Friday after today; a bare "Friday" or "this Friday" may mean today.
- **Dates** like `12/11/2026` are read day-first (Indian convention).
- **Confidence scores:** OCR confidence is Tesseract's average word confidence; typed text is 1.0. Entity confidence is a heuristic based on how many entities were found.
- **Departments** map keywords (e.g. "dentist") to canonical names (e.g. "Dentistry"). Add more in `DEPARTMENT_MAP` in `entities.py`.

## Limitations and future work

- Handwritten notes are unreliable with Tesseract; clean printed text works best.
- Unusual phrasing ("tooth doctor") isn't recognized. An LLM fallback for entity extraction and validation of the final result would address this.
- Only the first date/time/department found in the text is used.