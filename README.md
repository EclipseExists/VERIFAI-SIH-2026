# VERIFAI-SIH-2026
**Explainable AI-Powered Identity & Document Risk Screening | SIH 2026 PS-188**

---

## OCR + MRZ Subsystem (Member 2 Track)

This subsystem handles document image preprocessing, OCR text extraction, Machine Readable Zone (MRZ) detection, ICAO Doc 9303 TD3 format parsing, checksum validation, and tampering risk analysis.

### Pipeline Architecture

```text
Passport Image
      ↓
Preprocessing (CLAHE, Bilateral Denoise, Deskew, Binarization)
      ↓
OCR Engine (PaddleOCR / Mock)
      ↓
Raw OCR Text + Polygons + Confidence
      ↓
MRZ Multi-factor Detection (Charset Purity, Length, Spatial Geometry)
      ↓
Controlled Error Correction (Evidence-based O/0, I/1, B/8 substitutions)
      ↓
TD3 MRZ Parsing (Names, Passport Number, Nationality, DOB, Sex, Expiry)
      ↓
ICAO 9303 Checksum Validation (7-3-1 Modulo 10 Check Digits & Composite)
      ↓
Structured Passport Data & Tampering Risk Indicators
```

---

## Installation

```bash
pip install -r requirements.txt
```

---

## Python Usage

```python
from ocr_mrz import process_passport

# Process passport image from file path
result = process_passport("data/passports/passport_genuine.png")

if result.success and result.mrz_present:
    print(f"Holder Name:     {result.identity.name}")
    print(f"Passport Number: {result.identity.passport_number}")
    print(f"Nationality:     {result.identity.nationality}")
    print(f"Date of Birth:   {result.identity.date_of_birth}")
    print(f"Expiry Date:     {result.identity.expiry_date}")
    print(f"Checksum Valid:  {result.mrz_validation.overall}")
    print(f"Tampering Risk:  {result.risk.tampering_detected}")
```

---

## CLI Runner

```bash
# Run on an image
python -m ocr_mrz.cli data/passports/passport_genuine.png

# Fast test run with mock engine
python -m ocr_mrz.cli data/passports/passport_genuine.png --mock
```

---

## Backend Team Integration

For teammates integrating with `backend/app/api/ocr.py` and `backend/app/api/mrz.py`:

```python
# MRZ extraction & checksum validation
from ai.mrz.parse import parse_mrz
mrz_result = parse_mrz("path/to/document.png")

# OCR text and structured fields
from ai.ocr.extract import run_ocr
ocr_result = run_ocr("path/to/document.png")
```

---

## Running Tests

```bash
pytest -v
```
