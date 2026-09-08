# 🎨 VERIFAI — Frontend Developer Handoff Guide

Welcome to VERIFAI! This document contains everything you need to know to build the frontend User Interface (React, Next.js, Vue, etc.) and wire it up to our backend. 

The backend is 100% complete, integrated with 5 different AI models, and exposes a clean REST API via FastAPI.

---

## 🏗️ 1. Architecture & Features

VERIFAI is a **Human-in-the-Loop Decision Support System** for border officers. We do not auto-reject passengers. Instead, we run their documents through 5 AI modules and present a "Risk Dashboard" to the officer.

### The 5 Core Features (AI Modules)
1. **OCR (Optical Character Recognition):** Extracts names, DOB, and expiry dates from the passport image.
2. **MRZ (Machine Readable Zone):** Parses the `<<<` text at the bottom of the passport and validates standard ICAO checksums. If a checksum fails, the passport is forged.
3. **Forensics (ELA & Noise):** Scans the image at the pixel level to detect Photoshop, digital tampering, or copy-pasted text.
4. **Face Verification:** Compares the photo printed on the passport against a live "probe" photo of the passenger.
5. **Risk Engine:** A deterministic rules engine. It gathers the results from the 4 modules above, validates date chronologies (e.g., expiry > issue date), and calculates a final risk score (0-100) and risk band (Low, Medium, High).

---

## 🚀 2. How to Start the Backend (Local Dev)

To build the UI, you need the backend running locally. Open your terminal in the project root:

```bash
# 1. Start the PostgreSQL database (Make sure Docker is running)
docker compose up postgres -d

# 2. Setup Python environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# 3. Start the API server
cd backend
uvicorn app.main:app --reload --port 8000
```

> **🔥 CRITICAL:** Once the server is running, open **http://localhost:8000/docs**. This is the interactive **Swagger UI**. It is your best friend. It shows every exact JSON payload, data type, and lets you test endpoints directly from the browser.

*(Note: CORS is already configured to allow `*`. You will not get CORS errors when calling from `localhost:3000` or `localhost:5173`).*

---

## 🛣️ 3. The Integration Strategy (Step-by-Step Flow)

To make the UI feel incredibly fast and professional, you should orchestrate the API calls using a **Parallel Execution** strategy. 

Here is the exact JavaScript/TypeScript blueprint you should use in your frontend application.

### The JavaScript Blueprint

```javascript
// Example using Axios (or use fetch)
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

async function processPassenger(passportFile, livePhotoFile) {
    // ==========================================
    // STEP 1: Create a new screening case
    // ==========================================
    const caseRes = await axios.post(`${API_BASE}/cases`, { 
        subject_name: "Unknown Passenger" 
    });
    const caseId = caseRes.data.id;

    // ==========================================
    // STEP 2: Upload the Passport Document
    // ==========================================
    const formData = new FormData();
    formData.append("file", passportFile);
    
    const docRes = await axios.post(`${API_BASE}/cases/${caseId}/documents`, formData);
    const docId = docRes.data.id;

    // ==========================================
    // STEP 3: Run Heavy AI Models IN PARALLEL ⚡
    // ==========================================
    // Do not await these one by one! Promise.all runs them simultaneously.
    // (Show a "Analyzing Document..." loading spinner in UI here)
    await Promise.all([
        axios.post(`${API_BASE}/documents/${docId}/ocr`),
        axios.post(`${API_BASE}/documents/${docId}/mrz`),
        axios.post(`${API_BASE}/documents/${docId}/forensics`)
    ]);

    // ==========================================
    // STEP 4: Run Face Verification
    // ==========================================
    // In a real app, you'd upload the live photo. For this prototype,
    // you can pass the path to the dummy live photo provided in the repo.
    await axios.post(`${API_BASE}/cases/${caseId}/face-verification`, {
        document_id: docId,
        probe_face_path: "data/passports/passport_genuine.png" // using dummy for now
    });

    // ==========================================
    // STEP 5: Calculate Final Risk Score
    // ==========================================
    // The Risk Engine reads the DB and scores everything.
    await axios.post(`${API_BASE}/cases/${caseId}/risk-assessment`);

    // ==========================================
    // STEP 6: Fetch the "God Endpoint" for UI
    // ==========================================
    // Instead of stitching data together yourself, this returns 
    // the ENTIRE case + all AI results in one clean JSON object.
    const dashboardData = await axios.get(`${API_BASE}/cases/${caseId}/full`);
    
    return dashboardData.data;
}
```

---

## 📦 4. The Data Payload (What you receive)

When you call `GET /api/v1/cases/{case_id}/full`, this is exactly what you get back. You can use this JSON structure right now to start building your React interfaces, components, and props:

```json
{
  "case": {
    "id": "e4b294...-...",
    "status": "reviewed",
    "subject_name": "Unknown Passenger",
    "risk_score": 85.5,
    "risk_band": "high",
    "created_at": "2026-09-08T18:00:00Z"
  },
  "documents": [
    {
      "id": "abc123...",
      "image_path": "uploads/...",
      "original_filename": "passport.png"
    }
  ],
  "ocr": {
    "raw_text": "P<UTOERIKSSON<<ANNA...",
    "structured_fields": {
      "name": "ERIKSSON ANNA",
      "dob": "1985-08-14",
      "doc_number": "L898902C3",
      "expiry": "2030-08-14"
    },
    "field_confidence": { "name": 0.99, "dob": 0.98 }
  },
  "mrz": {
    "mrz_present": true,
    "checksum_valid": false,
    "parsed_fields": { "nationality": "UTO", "sex": "F" }
  },
  "forensics": {
    "overall_manipulation_probability": 0.92,
    "ela_score": 0.88,
    "noise_inconsistency_score": 0.95
  },
  "face_verification": {
    "similarity_score": 0.21,
    "band": "mismatch",
    "error_message": null
  },
  "risk_assessment": {
    "overall_score": 85.5,
    "risk_band": "high",
    "signals": [
      {
        "signal_name": "mrz_checksum_failure",
        "direction": "increases_risk",
        "magnitude": 40.0,
        "explanation": "MRZ checksum validation failed. Per ICAO 9303, this indicates the document data may have been altered.",
        "source_module": "mrz"
      },
      {
        "signal_name": "face_mismatch",
        "direction": "increases_risk",
        "magnitude": 45.0,
        "explanation": "Face similarity score 0.21 — below mismatch threshold. Person's face does not match the document photo.",
        "source_module": "face"
      }
    ]
  }
}
```

## 🎨 5. UI/UX Suggestions for the Dashboard
1. **The Traffic Light System:** Use the `risk_band` heavily in your UI. 
   - `low` = Green (Proceed)
   - `medium` = Yellow/Orange (Inspect Manually)
   - `high` = Red (Escalate/Reject)
2. **Explainability Cards:** The `risk_assessment.signals` array is the most important part of the app. Render these as a list of alert cards so the officer knows *exactly why* the AI gave that score.
3. **Data Comparison:** Put the `ocr.structured_fields` side-by-side with the `mrz.parsed_fields` so the officer can visually see if the printed text matches the MRZ text.

## ⚠️ 6. Error Handling Notes
Our backend is robust. If the Face module fails to find a face, it doesn't crash the server with a 500 error. It returns a `422 Unprocessable Entity`, and safely stores a record with an `error_message`. 

Your frontend shouldn't crash if one API call fails. Wrap your parallel calls in try/catch blocks, and the `GET /full` endpoint will simply return `null` for the modules that failed, allowing the dashboard to still render the working parts!

