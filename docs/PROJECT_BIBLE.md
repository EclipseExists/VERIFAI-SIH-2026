# VERIFAI — Project Bible
### Explainable AI-Powered Identity & Document Risk Screening
**SIH 2026 · PS-188 · Team Reference Document · v1.0**

---

## 0. How to Use This Document

This is the single source of truth for scope, architecture, and decisions. Every teammate should be able to answer "why are we building it this way" by pointing to a section here. Update it as decisions change — don't let code and this document drift apart.

---

## 1. Exact Interpretation of the Problem

Border and checkpoint officers currently verify passports, visas, permits and travel documents largely by eye, against time pressure, with no structured second opinion. Two failure modes matter:

- **False negatives**: a tampered document or impersonated identity passes because a subtle forgery signal (font kerning, resampling artifact, MRZ checksum mismatch, cross-document inconsistency) is invisible to a human working in seconds.
- **False positives**: a genuine traveller is delayed because an officer's gut instinct isn't backed by evidence, so there's no efficient way to justify escalation or de-escalation.

**What VERIFAI actually is**: a decision-support tool that ingests a document (and optionally a live face capture) and produces a structured, evidence-backed **risk profile** — not a verdict. It never says "this person is a criminal" or "this document is fake." It says "these five signals are inconsistent with a genuine document, here is the evidence for each, and here is a suggested priority level for human review."

**What VERIFAI is explicitly not**:
- Not a facial recognition surveillance system searching real-world watchlists.
- Not connected to any actual government database (Passport Seva, CID, Interpol, etc.).
- Not an autonomous gate — no auto-accept/auto-reject without a human in the loop.
- Not a claim of forensic/legal-grade document authentication.

This framing matters for the judges as much as for the build: SIH problem statements in this space are frequently over-promised ("we detect 99.2% of fake passports using deep learning"). Credibility comes from *scoping honestly* and *demonstrating real signal processing* on synthetic data, not from unverifiable accuracy claims.

---

## 2. User Personas

| Persona | Role | Goals | Frustrations Today |
|---|---|---|---|
| **Officer Priya** | Checkpoint/immigration officer | Fast, defensible decisions; wants evidence, not a black box | No time to cross-check MRZ manually; forgery cues are subtle |
| **Supervisor Arjun** | Shift supervisor / reviewing authority | Oversight, audit trail, escalation patterns | No structured record of *why* something was flagged |
| **Auditor Meera** | Post-hoc compliance/audit reviewer | Reconstruct what happened for a flagged case | Paper trails are inconsistent, no evidence chain |
| **System Admin Dev** | IT admin at checkpoint | Uptime, data retention rules, access control | Ad-hoc tools with no logging or role separation |

Every persona above interacts with the same dashboard but different permission levels — this becomes your RBAC model (Section 20).

---

## 3. User Journey

1. Traveller presents a document (and/or stands for a live capture).
2. Officer scans/uploads the document image(s) into VERIFAI.
3. System runs image quality checks — if unusable, prompts re-capture.
4. OCR + MRZ extraction populate a structured record; officer visually confirms extracted fields against the physical document (human always in the loop at this checkpoint).
5. System runs document validation, forensic analysis, face verification (if a live capture or second document is provided), and cross-document consistency checks.
6. Risk engine aggregates signals into a **risk band** (Low / Medium / High) with an **explanation panel** listing each contributing signal, its direction (risk-increasing/decreasing), and confidence.
7. Officer reviews evidence, makes the actual decision, and records a disposition (cleared / escalated / referred) — this human decision is logged.
8. Case record + evidence + officer decision are stored for audit; a report can be exported.
9. Supervisor can review flagged/escalated cases in an aggregate dashboard.

---

## 4. Functional Requirements

**Must**
- Upload/capture document image(s) and optional live face photo.
- Image quality gate (blur, glare, crop, resolution) before processing.
- OCR extraction of visible fields.
- MRZ zone detection, parsing, and checksum validation (where MRZ present).
- Rule-based document validation (date logic, format checks, field presence).
- Forensic signal extraction (see Section 15) with visual highlighting.
- Face verification between document photo and live/second-document photo.
- Cross-document consistency check across 2+ uploaded documents.
- Explainable risk score with per-signal breakdown.
- Officer dashboard: case view, evidence view, decision capture.
- Case audit log (immutable, timestamped, who-did-what).
- Exportable case report (PDF).

**Should**
- Role-based access (officer vs supervisor vs admin).
- Case history / search across past cases.
- Synthetic dataset generator/utility for demoing tampering scenarios.
- Configurable risk-weighting (so judges/officers can see the system isn't a fixed black box).

**Could**
- Batch processing mode.
- Multi-language OCR support (regional scripts).
- Analytics dashboard (flag rates, common inconsistency types).

---

## 5. Non-Functional Requirements

| Category | Target (hackathon-realistic) |
|---|---|
| Latency | End-to-end single-document screening in under ~8–15s on modest hardware (CPU-bound OCR/CV is slow — set expectations accordingly, or use lightweight models) |
| Explainability | Every risk contribution must be traceable to a concrete signal, never a raw opaque score |
| Auditability | Every case is immutable once finalized; all officer actions logged with timestamp + user id |
| Privacy | No real PII in demo; synthetic data only; face embeddings not raw images stored where possible |
| Availability | Not a hackathon concern beyond "runs reliably during the demo" — say so honestly, don't claim SLAs |
| Portability | Should run locally / on a single demo machine without cloud dependency, for judging-room reliability |

---

## 6. System Architecture (High Level)

```
                         ┌─────────────────────────┐
                         │   React/Next.js Frontend │
                         │  (Officer Dashboard UI)  │
                         └────────────┬─────────────┘
                                      │ REST/HTTPS
                         ┌────────────▼─────────────┐
                         │   FastAPI Backend (API)   │
                         │  Auth · Orchestration ·   │
                         │  Case Mgmt · Audit Log     │
                         └───┬───────┬───────┬───────┘
                             │       │       │
              ┌──────────────┘   ┌───▼───┐   └────────────────┐
              │                  │       │                    │
     ┌────────▼────────┐ ┌───────▼──────┐ ┌───────────▼──────────┐
     │  OCR + MRZ       │ │ Forensics /  │ │  Face Verification    │
     │  Extraction      │ │ Tampering    │ │  Module                │
     │  Service         │ │ Analysis     │ │                        │
     └────────┬─────────┘ └──────┬───────┘ └───────────┬───────────┘
              │                  │                     │
              └──────────┬───────┴──────────┬──────────┘
                          │                  │
                 ┌────────▼────────┐ ┌───────▼────────┐
                 │ Cross-Document   │ │  Risk Engine    │
                 │ Consistency      │ │  (rule + ML     │
                 │ Engine           │ │  aggregation)   │
                 └────────┬────────┘ └───────┬────────┘
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  Explainability     │
                          │  Layer (evidence     │
                          │  bundle generator)   │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │  PostgreSQL         │
                          │  (cases, evidence,  │
                          │  audit, users)       │
                          └─────────────────────┘
```

Each CV/AI service can be a Python module called in-process for the hackathon (simpler, faster to build) rather than separate microservices — don't over-engineer this into Kubernetes-grade infra you won't finish.

---

## 7. Module-by-Module Architecture

1. **Ingestion & Quality Gate** — accepts image, runs blur/glare/resolution/crop checks (OpenCV: Laplacian variance for blur, histogram checks for glare), rejects or flags before wasting downstream compute.
2. **OCR Extraction** — PaddleOCR (or Tesseract as fallback) extracts raw text + bounding boxes.
3. **Field Structuring** — maps raw OCR text to structured fields (name, DOB, document number, nationality, expiry) using layout heuristics/regex per document type.
4. **MRZ Module** — detects MRZ zone, parses TD1/TD2/TD3 formats, validates checksums.
5. **Document Validator** — deterministic rule checks (expiry vs. today, DOB vs. issue date sanity, document number format per type, field-presence completeness).
6. **Forensics Module** — ELA (error level analysis), noise/compression-artifact analysis, face-region boundary analysis, font/text consistency checks.
7. **Face Verification Module** — face detection + embedding + cosine similarity between document photo and live/second capture.
8. **Cross-Document Consistency Engine** — field-by-field diff across 2+ submitted documents with fuzzy matching for OCR noise tolerance.
9. **Risk Engine** — aggregates all signals into a weighted, explainable score/band.
10. **Explainability Layer** — turns internal signal values into human-readable evidence statements + visual overlays.
11. **Case & Audit Service** — persistence, immutability, RBAC-gated retrieval.
12. **Dashboard Frontend** — case intake, evidence visualization, decision capture, case history.

---

## 8. Data Flow

```
Image(s) in → Quality Gate → OCR → Field Structuring → MRZ Parse/Validate
      ↘ (parallel) → Forensics Analysis
      ↘ (parallel, if 2nd image) → Face Verification
      ↘ (if 2+ docs) → Cross-Document Consistency
→ All signals converge → Risk Engine → Explainability Layer
→ Evidence Bundle + Risk Band → Officer Dashboard
→ Officer Decision → Case finalized → Audit Log + PostgreSQL
```

Each stage should degrade gracefully — e.g., if MRZ isn't present on a document, that signal is simply omitted from the risk aggregation (with the omission itself shown, not hidden).

---

## 9. API Architecture (indicative)

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/auth/login` | Officer/supervisor login |
| POST | `/api/v1/cases` | Create new screening case |
| POST | `/api/v1/cases/{id}/documents` | Upload document image to a case |
| POST | `/api/v1/cases/{id}/face-capture` | Upload live face image |
| POST | `/api/v1/cases/{id}/process` | Trigger full pipeline run |
| GET | `/api/v1/cases/{id}` | Fetch case + evidence bundle |
| GET | `/api/v1/cases/{id}/evidence` | Fetch structured evidence/risk breakdown |
| POST | `/api/v1/cases/{id}/decision` | Officer records final disposition |
| GET | `/api/v1/cases` | List/search cases (role-scoped) |
| GET | `/api/v1/cases/{id}/report` | Export PDF report |
| GET | `/api/v1/audit/{case_id}` | Fetch immutable audit trail |

Keep it RESTful and synchronous-with-polling for the hackathon; don't build a message queue unless you have time left over.

---

## 10. Database Schema (PostgreSQL, indicative)

```
users(id, name, role, employee_id, password_hash, created_at)

cases(id, created_by, status, opened_at, closed_at, disposition)

documents(id, case_id, doc_type, image_path, uploaded_at)

ocr_results(id, document_id, raw_text, structured_fields JSONB, confidence)

mrz_results(id, document_id, mrz_raw, parsed_fields JSONB, checksum_valid BOOLEAN)

forensic_signals(id, document_id, signal_type, score, region_bbox JSONB, notes)

face_verifications(id, case_id, doc_face_id, probe_face_id, similarity_score, match_bool)

consistency_checks(id, case_id, field_name, doc_a_value, doc_b_value, match_bool, severity)

risk_assessments(id, case_id, overall_score, risk_band, computed_at)

risk_signals(id, risk_assessment_id, signal_name, contribution_value, direction, explanation_text)

audit_log(id, case_id, actor_id, action, timestamp, details JSONB)
```

`risk_signals` is the table that makes explainability real — every row is one sentence in the officer's evidence panel.

---

## 11. AI/ML Architecture — Overview

VERIFAI is **not one classifier**. It is a pipeline of narrow, individually-explainable components whose outputs are combined by a transparent risk engine. This is deliberate: a single end-to-end "fake/genuine" neural net is (a) not trainable credibly without a real forged-document dataset you don't have, and (b) not explainable, which directly contradicts the differentiator you're pitching.

| Component | Approach | Why |
|---|---|---|
| OCR | Pretrained (PaddleOCR/Tesseract) | Mature, no training needed |
| MRZ parsing | Deterministic algorithm (ICAO 9303 spec) | Fully specified, no ML needed, very demo-reliable |
| Document validation | Rule engine | Deterministic, explainable, no model risk |
| Forensics | Classical CV signal processing (ELA, noise analysis) + optionally a lightweight pretrained tamper-cue model | Explainable by construction; avoids unverifiable accuracy claims |
| Face verification | Pretrained embedding model (e.g. via `face_recognition`/dlib or InsightFace/ArcFace-style embeddings) | Off-the-shelf, well-validated, no training needed |
| Risk aggregation | Weighted rule-based scoring, optionally a small interpretable model (logistic regression / decision tree) trained on synthetic labeled scenarios | Interpretable by design (see Section 18) |

---

## 12. OCR Pipeline

1. Pre-process: deskew, denoise, contrast-normalize (OpenCV).
2. Run PaddleOCR (or Tesseract fallback) to get text + bounding boxes + per-token confidence.
3. Layout-aware field mapping: use relative bounding-box position + regex/keyword anchors (e.g., "Date of Birth", "DOB") to assign OCR tokens to structured fields, since layouts vary by document type/country.
4. Confidence flagging: low-confidence tokens are shown to the officer for manual confirmation rather than silently trusted — this is both good UX and protects you from over-claiming accuracy.
5. Output: structured JSON of fields + confidence + source bounding boxes (for later visual highlighting).

**Hackathon-feasible.** OCR on printed document text with pretrained models is a solved problem; your work is the field-structuring and confidence-handling layer around it, not the OCR itself.

---

## 13. MRZ Pipeline

1. Detect MRZ zone (bottom band of passport/ID, fixed aspect-ratio heuristics or a lightweight detector).
2. OCR the MRZ zone specifically (MRZ uses a constrained OCR-B font — often more reliable than free-text OCR).
3. Parse according to ICAO Doc 9303 TD1/TD2/TD3 format rules (fixed-width fields: document type, issuing country, surname/given names, document number, nationality, DOB, sex, expiry date).
4. Run **check-digit validation** — MRZ fields include modulo-10 check digits; recompute and compare. This is a completely deterministic, well-specified, and demo-friendly forensic signal — a check-digit mismatch is a strong, explainable red flag.
5. Cross-check MRZ-parsed fields against the OCR-extracted visual-zone fields (name, DOB, doc number should match between the two — an authentic, well-known type of inconsistency check).

**Fully hackathon-feasible** and one of your most credible technical demonstrations, since the spec is public and deterministic.

---

## 14. Document Validation Strategy

Deterministic rules, not ML:

- Expiry date must be ≥ today (else "expired document" flag).
- Issue date must precede expiry date, and both must be plausible relative to DOB.
- Document number format must match the expected pattern for the declared document type/country (regex library, maintained as config, not hardcoded).
- Mandatory fields must all be present and non-empty.
- MRZ check digits must validate (Section 13).
- Field cross-match between MRZ and visual zone must agree.

Each rule produces a boolean + explanation string that flows directly into the risk engine — this layer alone is enough to build a genuinely useful, fully explainable component even before any CV/ML work is added.

---

## 15. Tampering / Forensics Strategy

Be honest about what's crediblydetectable at hackathon scale vs. what needs a real forensic dataset:

**Crediblydoable now (classical CV signal processing):**
- **Error Level Analysis (ELA)** — re-compress the image at a known JPEG quality and diff against the original; regions that were edited/pasted often show different compression error levels. Good visual "highlighted region" demo.
- **Noise consistency analysis** — estimate local noise level across regions; a spliced photo region often has different noise characteristics than the surrounding document.
- **Copy-move detection** — classical keypoint-matching (ORB/SIFT) to detect duplicated regions within the same image (a common cheap forgery technique).
- **Metadata inspection** — where available, check for editing-software signatures in EXIF (weak signal, but real and explainable).
- **Font/text-line consistency** — check that character spacing/baseline alignment is consistent across a text field (irregular kerning is a classic overlay-text cue).

**Needs substantial data/research (state as future work, don't fake it):**
- A trained deep-learning tamper classifier — needs a labeled dataset of real forged documents, which you don't have and shouldn't fabricate.
- Print-vs-scan / recapture detection with high reliability.

**Should remain future-production only:**
- Physical security-feature verification (holograms, UV features) — requires specialized hardware capture, out of scope for a software prototype.

Present each forensic signal as a *contributing signal with a confidence*, never as a binary fake/real verdict — this is both more honest and better matches how the risk engine is supposed to work.

---

## 16. Face Verification Strategy

1. Detect and align face in both the document photo and the live/probe photo (e.g., via a pretrained face detector such as RetinaFace/MTCNN or dlib's HOG detector).
2. Generate embeddings using a pretrained face-recognition model (e.g., `face_recognition` library built on dlib's ResNet, or an ArcFace/InsightFace pretrained model).
3. Compute cosine similarity (or the library's native distance metric) between embeddings.
4. Map similarity to a **verified / uncertain / mismatch** band using a documented threshold — state clearly that the threshold is a configurable, tunable parameter, not a certified biometric standard.
5. Feed the similarity score (not a hard boolean) into the risk engine so officers see the actual confidence, not just pass/fail.

**Important credibility note for judges**: this is face *verification* (1:1 comparison of two given photos), not face *recognition/identification* against a database. Never claim or imply a live watchlist search — you don't have one, and claiming it would be actively misleading.

---

## 17. Cross-Document Consistency Engine

When an officer submits 2+ documents for the same person (e.g., passport + visa, or passport + a second ID):

1. Normalize field values (case-folding, date-format normalization, whitespace).
2. Fuzzy-match each shared field (name, DOB, nationality, document number where applicable) using edit-distance tolerant matching to absorb minor OCR noise.
3. Flag mismatches by severity: **critical** (DOB or document number mismatch), **moderate** (name spelling variant beyond expected transliteration tolerance), **minor** (formatting-only difference).
4. Each flagged inconsistency becomes one explainable risk-signal row with the exact conflicting values shown side by side — this is one of your strongest, most literally "explainable" and easy-to-demo features.

---

## 18. Risk Engine Design

**Design principle: interpretable-by-construction, not a black box.**

Recommended approach for a hackathon:
- Start with a **weighted rule-based scoring system**: each signal (MRZ checksum fail, expiry violation, forensic anomaly score, face-mismatch score, consistency conflict severity) contributes a signed weight to a running score.
- Weights are stored as **editable configuration**, not hardcoded — this lets you demo "the officer/admin can tune sensitivity" live, which is a strong differentiator.
- Optionally, once you have a synthetic labeled dataset (Section 21), train a small **interpretable model** (logistic regression or a shallow decision tree) on the signal vector → risk label, and show its learned coefficients/feature importances as an additional explainability layer — but the rule-based system should remain the fallback/baseline, since it works with zero training data and is always explainable.
- Final output: an **overall score**, a **risk band** (Low/Medium/High), and the **full list of contributing signals** with direction and magnitude.

Avoid: a single opaque deep model that outputs "0.87 = fake" with no decomposition. That's exactly what you're positioning against.

---

## 19. Explainability Strategy

- Every risk-band decision must decompose into a **ranked list of contributing signals**, each with: signal name, direction (increases/decreases risk), magnitude/confidence, and a one-line plain-language explanation.
- Visual evidence: bounding-box overlays on the document image for OCR fields, MRZ zone, and any flagged forensic regions — "show, don't just tell" is very effective in a judging room.
- Explanation text should be templated from signal metadata (not free-text LLM generation) so it's guaranteed accurate and doesn't hallucinate — e.g., `"MRZ check digit mismatch on document number (expected 4, computed 7)"` generated directly from the validation result, not paraphrased by a language model.
- Provide a toggle for "why is this Low/Medium/High risk?" that expands the full signal list — this single feature is often what gets remembered in a demo.

---

## 20. Security / Privacy Strategy

- All data in the demo environment is synthetic; state this explicitly on every dashboard screen and in the report footer.
- Role-based access control: officer (create/view cases), supervisor (view all + escalation), admin (config/weights).
- Audit log is append-only (no update/delete on `audit_log` rows) — enforce at the DB level (no UPDATE/DELETE grants on that table for the app role) so it's a credible claim, not just a description.
- Passwords hashed (bcrypt/argon2), never stored plaintext.
- Face embeddings, where possible, stored instead of raw probe images to reduce biometric data retention (state this as the design intent even if the MVP stores images for demo simplicity — be honest about which is actually implemented).
- Document images encrypted at rest if time allows (state as should-build, not must-build, if not implemented).
- Do **not** claim compliance with any specific government security certification (e.g., CERT-In empanelment, ISO 27001) unless actually true — for a student prototype it will not be, and judges in this domain often specifically probe for this kind of overclaim.

---

## 21. Synthetic / Demo Data Strategy

- Generate synthetic "identity documents" using a template + your own generated/stock placeholder photos (never real people's IDs) — render fields (fake names, fake numbers, DOB) programmatically onto a mock passport/visa template you design.
- Create a small library of **deliberately tampered variants** of your own synthetic documents (edited expiry date, spliced photo region, altered MRZ digit) to demonstrate each forensic/validation signal firing correctly and explainably.
- Create matched "genuine pairs" and "inconsistent pairs" of synthetic multi-document cases to demo the cross-document consistency engine.
- For face verification, use consented team-member photos or clearly synthetic/generated faces — never scrape real people's photos without consent.
- Clearly label all synthetic assets and never claim they resemble a real production dataset.

---

## 22. Evaluation Strategy

Since you don't have (and shouldn't fabricate) a real forged-document dataset with ground truth:

- Build your own small **synthetic labeled test set** (from Section 21) with known ground truth (which documents are tampered, which pairs are inconsistent, which faces should/shouldn't match).
- Report **signal-level precision/recall on your synthetic set only**, and label it as such everywhere (e.g., "94% MRZ checksum-fail detection on our 40-sample synthetic test set" — never a bare, context-free "94% accuracy").
- For OCR/face verification, cite the pretrained model's own published benchmark (with source) rather than re-claiming it as your own result.
- Include a "known limitations of this evaluation" note in your own report — judges reward this kind of rigor far more than an inflated number.

---

## 23. Failure Modes

- Poor image quality (blur/glare/low-res) → OCR/MRZ/forensics degrade silently unless the quality gate catches it first (this is why Section 7's quality gate exists).
- Non-standard/unsupported document layouts → field-structuring heuristics may mis-map fields; must fail gracefully (flag as "low confidence," not silently wrong).
- Face verification lighting/pose sensitivity → similarity score should always be shown with its own confidence, never as a hard binary.
- Rule-engine over-triggering on legitimate edge cases (e.g., legal name changes, valid transliteration variants) → must be tunable and clearly explained, not opaque.
- OCR misreads on cursive/handwritten fields (visas sometimes have handwritten annotations) → out of scope for MVP, state explicitly.

---

## 24. Limitations (state these openly to judges)

- Trained on/tested against synthetic data only — no claim of real-world forged-document accuracy.
- Face verification is 1:1 comparison only, not identification against any database.
- No integration with any actual government system, watchlist, or ID registry.
- Forensic signals are indicative, not forensic-grade legal evidence.
- Physical security features (holograms, UV ink, microprint) are not assessed — this system is image-based only.
- System is a decision-support aid; final authority remains fully with the human officer.

---

## 25. Deployment Architecture (hackathon-scoped)

- Single demo environment: Docker Compose bundling FastAPI backend, PostgreSQL, and the Next.js frontend, runnable on one laptop for judging-room reliability (no dependency on live internet/cloud during the demo).
- Optional: deploy a hosted demo (e.g., a small cloud VM) for judges to try beforehand, but always have the local fallback ready — conference wifi is not to be trusted.
- No claims of horizontal scaling, load balancing, or production SLAs — say "designed to be containerized for future scaling" rather than claiming it's already there.

---

## 26. Recommended Repository Structure

```
verifai/
├── backend/
│   ├── app/
│   │   ├── api/                # FastAPI routers
│   │   ├── core/                # config, security, auth
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/
│   │   │   ├── ocr/
│   │   │   ├── mrz/
│   │   │   ├── validation/
│   │   │   ├── forensics/
│   │   │   ├── face_verification/
│   │   │   ├── consistency/
│   │   │   └── risk_engine/
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── app/ (Next.js routes)
│   ├── components/
│   └── lib/
├── synthetic_data/
│   ├── templates/
│   ├── generator_scripts/
│   └── sample_cases/
├── docs/
│   └── VERIFAI_Project_Bible.md   (this file)
└── docker-compose.yml
```

---

## 27. Development Milestones (indicative 6–8 week runway)

| Phase | Weeks | Deliverable |
|---|---|---|
| 1. Foundation | 1 | Repo setup, DB schema, auth, synthetic document templates |
| 2. Core pipeline | 2–3 | OCR, MRZ parsing/validation, document validator, basic dashboard |
| 3. Advanced signals | 4–5 | Forensics module, face verification, cross-document consistency |
| 4. Risk engine + explainability | 5–6 | Weighted scoring, evidence panel, visual overlays |
| 5. Polish | 6–7 | Audit log, report export, RBAC, UI polish |
| 6. Demo prep | 7–8 | Synthetic demo scenarios, judge Q&A prep, rehearsal |

Build vertically (one thin end-to-end slice first), not horizontally (don't perfect OCR before anything else works end to end) — a working thin pipeline by end of week 2–3 is more valuable than a polished single module.

---

## 28. Dependencies (indicative)

**Backend**: FastAPI, SQLAlchemy, Pydantic, PostgreSQL (psycopg2/asyncpg), python-jose (auth), passlib/bcrypt.
**OCR/CV**: OpenCV, PaddleOCR (or pytesseract as a lighter fallback), NumPy, Pillow.
**Face verification**: `face_recognition` (dlib-based) or InsightFace, depending on install complexity on your team's machines.
**MRZ**: a maintained open-source MRZ-parsing library, or implement the ICAO 9303 spec directly (recommended for learning + credibility).
**Frontend**: Next.js, React, Tailwind CSS, a charting library for the dashboard (Recharts or similar).
**Reporting**: a PDF-generation library (e.g., WeasyPrint or ReportLab) for case export.

Verify install/runtime feasibility on your actual dev machines early — face-recognition/dlib installs can be painful; have a fallback plan.

---

## 29. Recommended Learning Roadmap for Six Students

Suggested role split (adjust to actual interests):

1. **OCR/MRZ lead** — learns OpenCV basics, PaddleOCR/Tesseract, ICAO 9303 MRZ spec.
2. **Forensics/CV lead** — learns classical CV forensic techniques (ELA, noise analysis, keypoint matching).
3. **Face verification lead** — learns face detection/embedding pipelines, similarity metrics.
4. **Backend/API lead** — learns FastAPI, SQLAlchemy, auth, PostgreSQL schema design.
5. **Frontend/dashboard lead** — learns Next.js/React/Tailwind, data visualization, evidence UI patterns.
6. **Risk engine/data lead** — learns rule-engine design, synthetic data generation, evaluation methodology, and owns the "explainability" narrative end to end.

Shared foundation for everyone in week 1: Python fundamentals (if coming from C++), Git workflow, and a joint walkthrough of the full target pipeline so no one is siloed — every member should be able to explain the *whole* system to a judge, not just their module.

---

## 30. Technical Risks

- Face-recognition library installation friction across different OS/machines (mitigate: containerize early).
- OCR accuracy varying wildly across document photo quality (mitigate: strong quality gate + confidence display, not a promise of perfect OCR).
- Scope creep into "let's also train a deep tamper classifier" without a real dataset (mitigate: stick to Section 15's classical-CV scope).
- Integration time underestimated — six independently-built modules take real time to wire together (mitigate: build the thin end-to-end slice first, per Section 27).

---

## 31. Product Risks

- Judges may probe hard on "is this actually usable by a real officer or is it a science project?" — mitigate by keeping the officer UI genuinely fast and simple, not just a technical showcase.
- Overclaiming (fake accuracy numbers, implied government integration) will damage credibility more than a smaller, honest scope — this is the single biggest product risk for this problem statement category.
- Ethical/bias concerns with face verification across skin tones/lighting — acknowledge this explicitly as a known limitation of the pretrained model you use rather than ignoring it; judges in this domain increasingly ask about it directly.

---

## 32. What Should NOT Be Built

- Any real or simulated connection to actual government databases, watchlists, or Passport Seva/CID/Interpol systems.
- A live facial-recognition search against a "database of citizens."
- A trained deep-learning fake/genuine classifier presented as validated when it's actually trained on a handful of synthetic samples.
- Auto-decision/auto-gate logic that bypasses the human officer.
- Any claim of security certification, government approval, or production deployment.
- Overbuilt infrastructure (Kubernetes, microservices mesh, message queues) that consumes build time without demo value.

---

## 33. Features to Prioritize for the Hackathon MVP

1. End-to-end pipeline working on at least 3–5 well-chosen synthetic demo cases (genuine, tampered, inconsistent-pair, expired, MRZ-checksum-fail).
2. MRZ parsing + checksum validation (highly credible, fully deterministic, easy to demo).
3. Cross-document consistency engine (visually striking, easy to explain, doesn't need heavy ML).
4. Explainability panel with visual evidence overlays (this is your differentiator — invest here).
5. A clean, fast officer dashboard — polish this over adding more backend signals if time runs short.

---

## 34. Strongest Potential Differentiator vs. Other PS-188 Teams

Most competing teams will likely build **one classifier that outputs fake/genuine with a single accuracy number** — this is the default, expected, and least defensible approach under judge questioning.

VERIFAI's differentiator is the **explainability-first, multi-signal, human-in-the-loop architecture**: every risk score decomposes into named, evidence-backed signals; MRZ/consistency checks are deterministic and verifiably correct in front of judges (you can literally alter one digit live and show the checksum fail); and the system is explicitly positioned as officer-assistive rather than an oracle. This combination — technical depth *and* epistemic honesty about limitations — is rare in student submissions and tends to score very well with technical judges who've seen a dozen overclaimed "AI detects fake IDs" pitches that day.

---

## 35. Twenty Questions a Technical Judge Is Likely to Ask

1. What's your actual accuracy, and on what dataset?
2. How is this different from just running one deep-learning classifier?
3. What happens when the officer disagrees with the risk score?
4. How do you handle a document type/layout you've never seen?
5. Is any of this connected to a real government database? (Answer: no, and explain why not.)
6. How does your face verification handle different lighting, angles, or aging?
7. What's your false-positive rate, and what's the cost of a false positive here?
8. Can someone game your forensic detection by re-compressing/re-scanning the whole document uniformly?
9. How do you prevent bias in the face verification model across demographics?
10. What data did you train the risk engine on?
11. How do you validate MRZ checksum logic — is it the actual ICAO spec?
12. What happens with damaged/worn physical documents?
13. How is officer decision data secured and audited?
14. Could this system be attacked or spoofed (e.g., adversarial images)?
15. What's your plan if this needed to scale to a real checkpoint's throughput?
16. Why did you choose rule-based + explainable over an end-to-end deep model?
17. How do you handle non-English/regional-script documents?
18. What's stored, for how long, and who can access it?
19. How would this integrate with an actual immigration/border IT system in production?
20. What's the single biggest limitation of your current prototype?

Prepare a one-to-two-sentence honest answer for each — the "I don't know, here's how we'd find out" answer, delivered confidently, often scores better than a fabricated confident answer.

---

## Final Build Priority Summary

### A. MUST BUILD
- Image quality gate
- OCR extraction + structured field mapping
- MRZ parsing + checksum validation
- Deterministic document validation rules
- Face verification (1:1 similarity, pretrained model)
- Cross-document consistency engine
- Rule-based, weighted, explainable risk engine
- Evidence/explanation panel with visual overlays
- Officer dashboard (case intake → evidence → decision)
- Case + audit logging in PostgreSQL
- Synthetic demo dataset (genuine + tampered + inconsistent scenarios)

### B. SHOULD BUILD
- Role-based access control (officer/supervisor/admin)
- PDF case report export
- Configurable/tunable risk weights exposed in UI
- Classical forensic signals (ELA, noise analysis, copy-move detection)
- Case history/search

### C. NICE TO HAVE
- Interpretable ML model (logistic regression) layered on top of rule-based risk engine
- Batch processing mode
- Analytics/aggregate dashboard for supervisors
- Multi-language/regional-script OCR support
- Encrypted-at-rest document storage

### D. DO NOT BUILD
- Any real/simulated government database or watchlist integration
- Live facial-recognition search/identification against any "citizen database"
- Autonomous accept/reject decision-making without a human officer
- A trained deep tamper classifier presented as validated on real-world data
- Claims of security certification or production/government approval
- Heavy infrastructure (Kubernetes, service mesh, message queues) beyond hackathon needs

---

*End of Project Bible v1.0. Treat this as a living document — update it as design decisions are made during the build.*
