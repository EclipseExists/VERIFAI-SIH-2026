# 🎨 VERIFAI — Ultimate Frontend Integration Guide

Welcome to the frontend team! This guide contains **everything** you need to know, step-by-step, to build the React/Next.js dashboard and connect it to our completed AI backend.

---

## 🏗️ 1. What You Are Building
You are building a **Human-in-the-Loop Decision Support Dashboard** for Border Control Officers. 

The system does *not* automatically accept or reject passengers. It runs a passport image and a live photo through 5 different AI models, gathers the evidence, calculates a "Risk Score" (0-100), and presents this to the officer so they can make the final call.

Your dashboard needs:
1. **Upload Screen:** To upload the passport image.
2. **Loading Screen:** To show the AI models processing (OCR, MRZ, Forensics, Face).
3. **The Results Dashboard:** A beautiful layout showing the extracted text, forensic anomaly maps, the final Risk Band (Green/Yellow/Red), and the plain-English explanations for the AI's decision.

---

## 🚀 2. Local Setup (Getting the Backend Running)

To build your UI, you must have the backend running on your computer.

1. Open a terminal in the `VERIFAI-SIH-2026` folder.
2. Start the database (Requires Docker desktop to be open):
   ```bash
   docker compose up postgres -d
   ```
3. Start the API Server:
   ```bash
   source backend/venv/bin/activate  # (Mac/Linux)
   cd backend
   uvicorn app.main:app --reload --port 8000
   ```
4. Open **http://localhost:8000/docs**. This is the interactive API documentation (Swagger). It tells you exactly what data to send and what you will receive.

---

## 🛣️ 3. The Step-by-Step API Integration Flow

For the fastest, most reliable user experience, you should orchestrate the API calls using **Parallel Execution**. Here is the exact JavaScript code blueprint you can copy into your React app.

### The Code Blueprint
```javascript
import axios from 'axios';

const API_BASE = 'http://localhost:8000/api/v1';

async function processPassenger(passportImageFile) {
    try {
        // ==========================================
        // STEP 1: Create a new Case
        // ==========================================
        const caseRes = await axios.post(`${API_BASE}/cases`, { 
            subject_name: "Unknown Passenger" 
        });
        const caseId = caseRes.data.id;

        // ==========================================
        // STEP 2: Upload the Passport Image
        // ==========================================
        const formData = new FormData();
        formData.append("file", passportImageFile);
        
        const docRes = await axios.post(`${API_BASE}/cases/${caseId}/documents`, formData);
        const docId = docRes.data.id;

        // ==========================================
        // STEP 3: Run AI Models IN PARALLEL ⚡
        // ==========================================
        // This is crucial for speed. Do not wait for them one by one.
        await Promise.all([
            axios.post(`${API_BASE}/documents/${docId}/ocr`),
            axios.post(`${API_BASE}/documents/${docId}/mrz`),
            axios.post(`${API_BASE}/documents/${docId}/forensics`),
            // For hackathon: using a dummy path for the live face probe.
            axios.post(`${API_BASE}/cases/${caseId}/face-verification`, {
                document_id: docId,
                probe_face_path: "data/passports/passport_genuine.png" 
            })
        ]);

        // ==========================================
        // STEP 4: Calculate Final Risk Score
        // ==========================================
        await axios.post(`${API_BASE}/cases/${caseId}/risk-assessment`);

        // ==========================================
        // STEP 5: Fetch the Dashboard Data
        // ==========================================
        // This returns one massive, organized JSON object with EVERYTHING.
        const dashboardData = await axios.get(`${API_BASE}/cases/${caseId}/full`);
        
        return dashboardData.data;

    } catch (error) {
        console.error("Pipeline failed:", error);
        throw error;
    }
}
```

---

## 📦 4. The Data You Will Receive

When you make that final `GET /cases/{case_id}/full` call, you receive this exact JSON object. You can use this schema to start building your React components *right now*.

```json
{
  "case": {
    "id": "e4b294...",
    "status": "reviewed",
    "risk_score": 85.5,
    "risk_band": "high"
  },
  "ocr": {
    "structured_fields": {
      "name": "ERIKSSON ANNA",
      "dob": "1985-08-14",
      "doc_number": "L898902C3",
      "expiry": "2030-08-14"
    }
  },
  "mrz": {
    "checksum_valid": false,
    "parsed_fields": { "nationality": "UTO", "sex": "F" }
  },
  "forensics": {
    "overall_manipulation_probability": 0.92,
    "ela_image_path": "/Users/.../passport_genuine_ela.png",
    "noise_image_path": "/Users/.../passport_genuine_noise.png"
  },
  "face_verification": {
    "similarity_score": 0.21,
    "band": "mismatch"
  },
  "risk_assessment": {
    "overall_score": 85.5,
    "risk_band": "high",
    "signals": [
      {
        "signal_name": "mrz_checksum_failure",
        "direction": "increases_risk",
        "magnitude": 40.0,
        "explanation": "MRZ checksum validation failed. Document data may have been altered.",
        "source_module": "mrz"
      },
      {
        "signal_name": "face_mismatch",
        "direction": "increases_risk",
        "magnitude": 45.0,
        "explanation": "Face similarity score 0.21 — below mismatch threshold. Face does not match.",
        "source_module": "face"
      }
    ]
  }
}
```

---

## 🎨 5. UI/UX Checklist for the Hackathon
- [ ] **Risk Colors:** Use `risk_band` heavily. `low` = Green, `medium` = Yellow, `high` = Red.
- [ ] **Signal Explanations:** The `risk_assessment.signals` array is the most important part! Render each item as a warning card so the officer knows *why* the AI flagged it.
- [ ] **Visual Evidence:** The `forensics` object returns `ela_image_path` and `noise_image_path`. Display these images so the officer can physically see the Photoshop tampering.
- [ ] **Final Decision:** Provide two big buttons at the bottom of the dashboard: "Approve Passenger" and "Reject Passenger". 
  - To log their decision, make one final API call:
    `POST /api/v1/cases/{case_id}/decision` with body `{"decision": "approve", "notes": "Looks fine"}`.

