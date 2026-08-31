# VERIFAI — Architecture Decision Review v1
### Architecture-Validation Phase · Baseline: Project Bible v1.0
**No implementation code in this document. Decisions only.**

---

## How to Read This Document

Every item below is marked with a decision tag:
- **KEEP** — proceed as designed in the Project Bible.
- **TRIM** — keep the idea, cut the scope down to something six students can actually finish.
- **DEFER** — real idea, wrong phase; push to should-build or future-work.
- **CUT** — remove from the plan entirely; either not credible, not finishable, or not defensible under questioning.

This review exists to stop scope creep before a single line of code is written. Where this document disagrees with the Project Bible, **this document wins.**

---

## 1. Architecture Strengths to Keep Unchanged

- **Multi-signal, not single-classifier, design.** The decision to never build one opaque fake/genuine model is the single most important architectural decision in the whole project. Keep it exactly as is.
- **MRZ parsing + checksum validation as a first-class deterministic module.** ICAO 9303 is a public, fixed, well-specified format. This is your most reliable, most demo-safe, most judge-defensible component. Nothing about this needs to change.
- **Separation of risk *signals* from risk *aggregation*.** Storing each signal as its own row (`risk_signals`) rather than baking everything into one opaque number is correct and should not be simplified away, even under time pressure — it's the backbone of your explainability story.
- **Human-in-the-loop framing**, end to end: officer confirms OCR, officer makes the final disposition, system never auto-decides. Keep this as a hard architectural constraint, not just a talking point — it should be visible in the UI (no auto-accept button) and in the API (no endpoint that finalizes a case without an officer decision payload).
- **Synthetic-data-only stance.** Correct, and non-negotiable for a student team with no lawful access to real identity documents.

---

## 2. Parts Too Ambitious for Six Beginner/Intermediate Students

Be blunt: the original Bible describes a *fifteen-person production team's* roadmap. For six students learning most of this stack as they go, several pieces need to shrink or drop out of the MVP:

| Original scope | Problem | Decision |
|---|---|---|
| Full forensic suite (ELA + noise analysis + copy-move/keypoint matching + font-consistency + metadata) | Five distinct CV techniques, each with its own tuning and failure modes, owned by one "forensics lead" | **TRIM** to ELA + one noise/consistency check only for MVP |
| Interpretable ML model (logistic regression) layered on the risk engine | Requires a labeled synthetic dataset large and balanced enough to train meaningfully, plus a train/eval loop nobody on the team has done before | **DEFER** to nice-to-have; rule-based engine is the actual deliverable |
| Full RBAC with 3 distinct roles (officer/supervisor/admin) | Real auth complexity for a 6–8 week build with 10+ other modules | **TRIM** to 2 roles (officer, admin) for MVP; add supervisor later if time allows |
| "Potential identity linkage" module (synthetic biometric-record graph) | Conceptually powerful but easy to accidentally imply real biometric-database capability, and non-trivial to build honestly in the time available | **TRIM** heavily — see Section 4 |
| Batch processing mode | Real infra work for a feature judges rarely ask to see live | **DEFER** |
| Multi-language/regional-script OCR | OCR model tuning per script is its own project | **CUT** from MVP scope entirely; mention only as future work |
| Encrypted-at-rest storage | Legitimate concern, but genuinely secondary to getting the pipeline working; often the first thing silently dropped under deadline pressure — better to say so up front | **DEFER** |

**Rule of thumb going forward:** if a feature requires a technique no one on the team has implemented before *and* is not on the critical path to the demo narrative, it does not belong in the MVP.

---

## 3. Features That Are Technically Weak or Judge-Challengeable

- **Copy-move (keypoint matching) forgery detection.** Works cleanly on textbook examples, is fragile and prone to false positives on real-world-quality scanned images, and is exactly the kind of feature a technical judge will ask you to break live by uploading an unedited, slightly noisy photo. Weak enough that including it under time pressure is a net negative unless very carefully tuned and tested. **TRIM/CUT** — drop from MVP, mention only as future work if asked.
- **Font/text-line consistency check.** Sounds impressive, but is genuinely hard to make reliable on OCR'd real-world text without heavy calibration, and a judge who understands OCR will notice if it's shallow. **CUT** from MVP.
- **Metadata/EXIF inspection.** Trivially defeated by any re-save or screenshot, which most demo pipelines (including yours, since inputs are uploaded images) will already have stripped. Including it risks a judge asking "doesn't uploading strip this?" and you having no good answer. **CUT** — not worth the risk-to-value ratio.
- **Face verification threshold presented as a fixed pass/fail.** If similarity is shown as a hard boolean rather than a score + band, a judge will immediately ask "what's your threshold and how did you pick it?" and there's no good answer available to a six-person student team. **TRIM** — always show the raw score, with the band as a suggestion, never the sole output.
- **"Identity linkage" as originally scoped.** As written it risks sounding like you're claiming cross-database biometric matching capability. That's a serious credibility risk in this specific problem-statement category, where judges are primed to look for exactly this kind of overclaim. **TRIM** — reduce to a clearly-labeled toy demo: a small local table of 4–5 synthetic "prior records," explicitly narrated as "a stand-in for what a real production system would query, not a real capability."

---

## 4. Claims That Must Be Avoided

State these as hard rules for every teammate, in every slide, in every conversation with a judge:

1. Never say or imply the system is connected to, tested against, or compatible with any real government database, watchlist, or ID registry.
2. Never state a bare accuracy percentage without immediately naming the (synthetic, small) dataset it came from.
3. Never call face verification "face recognition" or imply identification against a population — it is 1:1 comparison of two supplied images only.
4. Never claim forensic findings are legally or evidentiarily conclusive — they are indicative signals for human review.
5. Never claim any security certification, government approval, or production-readiness.
6. Never claim the system detects "all types of forgery" — name the specific signal classes it checks and stop there.
7. Never present the risk score as the system's decision — always describe it as input to the officer's decision.
8. Never claim real-time performance guarantees you haven't actually measured on your own hardware.

---

## 5. AI Components That Should Use Pretrained Models

| Component | Recommended approach |
|---|---|
| OCR | PaddleOCR or Tesseract, pretrained, no fine-tuning |
| Face detection | Pretrained detector (dlib HOG/CNN, or MediaPipe Face Detection — MediaPipe is often a lighter, more reliable install for beginners than dlib) |
| Face embedding/verification | Pretrained embedding model (`face_recognition`/dlib, or DeepFace as a simpler wrapper if install issues arise) |

No component in VERIFAI should involve training a model from scratch. If any teammate proposes training a custom CNN "for accuracy," the answer is no — there is no dataset to train it on honestly, and a mediocre home-trained model is a bigger credibility risk than a well-used pretrained one.

---

## 6. Components That Should Remain Deterministic/Rule-Based

| Component | Why deterministic |
|---|---|
| MRZ parsing + checksum validation | Fully specified by ICAO 9303 — there is no ML version of this that is better |
| Document field validation (expiry, date logic, format regex) | Simple boolean logic, fully explainable, zero training data needed |
| Cross-document consistency matching | Fuzzy string matching (edit distance) is deterministic and sufficient — no ML needed |
| Risk aggregation (MVP) | Weighted rule-based scoring, fully transparent, configurable live in front of judges |
| Quality gate (blur/resolution check) | Simple statistical thresholds (e.g., Laplacian variance) — deterministic and reliable |

This is a deliberate majority-deterministic architecture. That is a **feature**, not a limitation — say so explicitly in your pitch.

---

## 7. Real Data vs. Synthetic Data, Component by Component

| Component | Data requirement |
|---|---|
| MRZ/document validation logic | No dataset needed — logic is spec-derived, tested against hand-built synthetic examples |
| OCR | Uses the pretrained model's own training data (not yours); your synthetic documents are only test inputs |
| Face verification | Uses the pretrained model's own training data; your test inputs are consented team-member photos or clearly synthetic faces — **never scraped real people's photos** |
| Forensics (ELA/noise) | No training data needed — signal-processing techniques, tested against your own deliberately-edited synthetic documents |
| Risk engine (rule-based) | No dataset needed for MVP |
| Risk engine (optional ML layer, deferred) | Would need a synthetic labeled dataset you construct yourselves — clearly label it as such if you ever build this |

**No component in this system requires, uses, or should ever be described as using real government-issued identity or biometric data.**

---

## 8. Components That Can Realistically Produce a Convincing Live Demo

Ranked by demo strength — this ordering should directly inform what you show first when judges are in front of you:

1. **MRZ checksum failure** — alter one digit in a synthetic passport, show the system catch it instantly and explain exactly why. Deterministic, fast, impossible to argue with.
2. **Cross-document field mismatch** — upload two synthetic documents with a deliberately mismatched DOB, watch the system flag it with both values shown side by side.
3. **Expired document / date-logic violation** — trivial to trigger, instantly explainable.
4. **Face verification score** — show a matching pair and a non-matching pair side by side with their similarity scores.
5. **ELA-highlighted tampered region** — visually the most impressive, but keep expectations calibrated; walk in with 2–3 pre-tested examples you know work well rather than improvising on a judge's photo.
6. **Explainability panel expanding to show every contributing signal** — this is the moment that ties the whole pitch together; don't rush past it.

Weaker/riskier for live demo (rehearse heavily or avoid entirely): copy-move detection, font-consistency checks — both already flagged for removal in Section 3.

---

## 9. Features to Remove from the MVP

Consolidating the CUT/heavy-TRIM decisions above into one explicit list:

- Copy-move/keypoint forgery detection
- Font/text-line consistency analysis
- Metadata/EXIF inspection
- Interpretable ML model layered on the risk engine
- Three-tier RBAC (supervisor role)
- Batch processing mode
- Multi-language/regional-script OCR
- Encrypted-at-rest storage
- Full "identity linkage" feature as originally scoped (replaced by a small, explicitly-labeled toy version — see Section 3)

---

## 10. Primary Differentiators (What VERIFAI Should Be Known For)

1. **Deterministic MRZ validation done correctly**, per actual ICAO spec — most student teams will not bother to implement this properly, and it's checkable/impressive on the spot.
2. **Full signal-level explainability** — every risk point traceable to a named, human-readable reason, never a bare score.
3. **Cross-document consistency engine** — cheap to build, very easy to demo, directly maps to a real officer workflow (comparing passport vs. visa).
4. **Explicit, visible human-in-the-loop design** — no auto-accept/reject anywhere in the UI or API, stated as a design principle, not an afterthought.
5. **Honesty about limitations as a feature of the pitch itself** — a dedicated "what this system does not claim to do" slide is unusual, memorable, and defuses most judge attacks before they're asked.

---

## 11. Minimum Viable End-to-End Vertical Slice

Before building any additional signal or polish, the team should get this exact thin path working, in this order, on one synthetic passport:

```
Upload synthetic passport image
   → Quality gate passes
   → OCR extracts visible fields
   → MRZ zone detected, parsed, checksum validated
   → Rule-based document validation runs (expiry check, field presence)
   → Risk engine combines the (currently few) available signals into a score + band
   → Dashboard displays the document, extracted fields, and a basic explanation list
   → Officer records a disposition
   → Case is saved to PostgreSQL with an audit entry
```

No face verification, no forensics, no cross-document check yet. This slice alone proves the entire pipeline shape works, end to end, through a real database, with a real UI — everything after this point is *additive*, not structural.

---

## 12. Canonical Data Contracts Between Modules

These are the shapes each module hands to the next. Treat this as the interface contract the team agrees on *before* anyone writes code — it's what lets six people build modules in parallel without integration chaos later.

**DocumentImage** (input to OCR/MRZ/Forensics)
```
{
  "document_id": "uuid",
  "case_id": "uuid",
  "doc_type": "passport | visa | id_card | permit",
  "image_path": "string",
  "quality_check": { "passed": true, "blur_score": 0.0, "notes": "string" }
}
```

**OCRResult**
```
{
  "document_id": "uuid",
  "structured_fields": { "name": "string", "dob": "date", "doc_number": "string", "nationality": "string", "expiry": "date" },
  "field_confidence": { "name": 0.0, "dob": 0.0, "...": 0.0 },
  "raw_text": "string"
}
```

**MRZResult**
```
{
  "document_id": "uuid",
  "mrz_present": true,
  "parsed_fields": { "...": "..." },
  "checksum_valid": true,
  "checksum_details": [ { "field": "doc_number", "expected": 4, "computed": 7, "valid": false } ]
}
```

**ValidationResult**
```
{
  "document_id": "uuid",
  "checks": [ { "rule": "expiry_not_past", "passed": true, "explanation": "string" } ]
}
```

**ForensicSignal**
```
{
  "document_id": "uuid",
  "signal_type": "ela | noise_consistency",
  "score": 0.0,
  "region_bbox": [x, y, w, h] ,
  "explanation": "string"
}
```

**FaceVerificationResult**
```
{
  "case_id": "uuid",
  "doc_face_id": "uuid",
  "probe_face_id": "uuid",
  "similarity_score": 0.0,
  "band": "match | uncertain | mismatch"
}
```

**ConsistencyResult**
```
{
  "case_id": "uuid",
  "field_name": "string",
  "doc_a_value": "string",
  "doc_b_value": "string",
  "match": true,
  "severity": "critical | moderate | minor"
}
```

**RiskSignal** (the universal unit every module above ultimately produces)
```
{
  "case_id": "uuid",
  "signal_name": "string",
  "direction": "increases_risk | decreases_risk | neutral",
  "magnitude": 0.0,
  "explanation": "string",
  "source_module": "ocr | mrz | validation | forensics | face | consistency"
}
```

**RiskAssessment** (final output of the risk engine)
```
{
  "case_id": "uuid",
  "overall_score": 0.0,
  "risk_band": "low | medium | high",
  "contributing_signals": [ RiskSignal, RiskSignal, "..." ],
  "computed_at": "timestamp"
}
```

Every module's job, ultimately, is: consume its typed inputs, produce zero or more `RiskSignal` records. The risk engine's only job is to consume a list of `RiskSignal` and produce one `RiskAssessment`. This contract is what keeps the architecture honestly modular rather than becoming six students' code awkwardly glued together in week 7.

---

## 13. Exact Order of Implementation

1. Repo scaffolding, Docker Compose, PostgreSQL schema (trimmed to MVP tables only), auth (2 roles).
2. Synthetic document template + generator for at least one document type (passport).
3. Image quality gate.
4. OCR extraction + field structuring for that one document type.
5. MRZ parsing + checksum validation.
6. Rule-based document validation.
7. Minimal risk engine (handles whatever signals exist so far) + minimal dashboard showing a case end to end. **← Vertical slice from Section 11 complete here. Do not proceed past this point until this works reliably.**
8. Second synthetic document type + cross-document consistency engine.
9. Face verification module.
10. Forensics module (ELA + one noise/consistency signal only).
11. Full explainability panel with visual bounding-box overlays.
12. Audit logging, case history/search, PDF report export.
13. UI polish, demo scenario rehearsal, judge Q&A prep (Section F below).

Anything from Section 2's DEFER/CUT list only gets attempted after step 13 is solid and there is verified spare time — not before.

---

## A. FINAL MVP

- Image quality gate (blur/resolution)
- OCR extraction + structured field mapping (one document type minimum, second type if time allows)
- MRZ parsing + checksum validation
- Deterministic document validation rules
- Cross-document consistency engine
- Face verification (1:1, pretrained model, score + band, never hard boolean)
- ELA + one additional forensic signal (noise consistency)
- Rule-based, weighted, configurable risk engine
- Full explainability panel with visual evidence overlays
- Officer dashboard: case intake → evidence → decision
- 2-role auth (officer, admin)
- Case + audit logging in PostgreSQL
- Synthetic demo dataset covering: genuine, tampered, inconsistent-pair, expired, MRZ-checksum-fail scenarios

## B. DIFFERENTIATORS

- Spec-correct, live-breakable MRZ checksum validation
- Full signal-level explainability (never a bare score)
- Cross-document consistency engine as a first-class, easy-to-demo feature
- Explicit, architecturally-enforced human-in-the-loop design
- Open acknowledgment of limitations as part of the pitch itself

## C. FUTURE FEATURES

- Interpretable ML layer on top of the rule-based risk engine
- Three-tier RBAC (supervisor role)
- Batch processing mode
- Multi-language/regional-script OCR
- Encrypted-at-rest document storage
- Expanded "identity linkage" as a real feature (with a real, larger synthetic dataset and much more careful framing)
- Copy-move detection and font-consistency analysis, if properly tuned and validated later

## D. OUT OF SCOPE

- Any real or simulated connection to government databases, watchlists, or ID registries
- Live facial-recognition search/identification against any population or "citizen database"
- Autonomous accept/reject decision-making without a human officer
- Training any model from scratch
- Any claim of security certification or production/government approval
- Kubernetes/service-mesh/message-queue infrastructure
- Metadata/EXIF-based forensic checks

## E. TOP 15 TECHNICAL RISKS

1. Face-recognition/dlib library installation failures across different student machines/OS.
2. OCR field-structuring heuristics breaking on any layout not explicitly tested.
3. Integration time between six independently-built modules underestimated.
4. Forensic signals producing false positives on ordinary low-quality (not tampered) synthetic photos.
5. MRZ zone detection failing on non-standard synthetic document crops/angles.
6. Risk engine weights not tuned, producing a demo where everything scores "Medium."
7. Database schema changes late in the build breaking already-written module code.
8. PostgreSQL/auth setup eating disproportionate time versus its demo value.
9. Face verification threshold picked arbitrarily with no justification ready for judges.
10. Team losing time trying to make copy-move detection reliable before it's cut per this review.
11. No teammate owning integration/end-to-end testing specifically, so the vertical slice never gets validated as a whole.
12. Synthetic document templates looking too obviously fake, undermining demo believability.
13. Explainability panel becoming a wall of technical text instead of readable evidence.
14. Live demo relying on internet/cloud availability at judging time.
15. Last-minute feature additions (from the CUT/DEFER lists) reintroduced under pressure, breaking the working vertical slice.

## F. TOP 15 JUDGE ATTACKS

1. "What's your accuracy, and on what dataset?"
2. "Is this connected to any real government system?"
3. "How is this different from one deep-learning classifier?"
4. "What happens when the officer disagrees with the score?"
5. "Doesn't uploading strip EXIF metadata, making that check useless?" *(pre-empted by cutting this signal — Section 3)*
6. "How do you pick your face-verification threshold?"
7. "Can I upload my own photo right now and break your forensics module?"
8. "What's your false-positive rate and what does a false positive cost a real traveller?"
9. "How do you handle bias in the face verification model across demographics?"
10. "What happens with a document type or layout you've never tested?"
11. "Is this forensic evidence legally admissible?"
12. "How would this scale to real checkpoint throughput?"
13. "Who can access this data, and for how long is it stored?"
14. "What's the single biggest limitation of your current system?"
15. "Why should an officer trust your risk score at all?"

Every one of these has a prepared, honest, one-to-two-sentence answer somewhere in this document or the Project Bible. Rehearse them as a team before the internal round — a confident honest answer consistently outperforms a confident fabricated one with technical judges.

## G. FINAL ARCHITECTURE DIAGRAM (MVP, post-review)

```
                    ┌───────────────────────────┐
                    │  React/Next.js Frontend    │
                    │  Officer Dashboard          │
                    └─────────────┬──────────────┘
                                  │ REST/HTTPS
                    ┌─────────────▼──────────────┐
                    │   FastAPI Backend           │
                    │  Auth (officer/admin) ·      │
                    │  Case Orchestration ·        │
                    │  Audit Log                   │
                    └──┬─────────┬─────────┬──────┘
                       │         │         │
           ┌───────────▼──┐ ┌────▼─────┐ ┌─▼──────────────┐
           │ Quality Gate  │ │  OCR +   │ │  MRZ Parser +    │
           │ (blur/res)    │ │  Field   │ │  Checksum         │
           │               │ │  Mapping │ │  Validator         │
           └───────┬───────┘ └────┬─────┘ └─────────┬────────┘
                   │              │                 │
                   └──────┬───────┴─────────┬───────┘
                          │                 │
              ┌───────────▼──────┐ ┌────────▼─────────┐
              │ Document          │ │  Forensics         │
              │ Validation Rules  │ │  (ELA + noise)      │
              └───────────┬──────┘ └────────┬─────────┘
                          │                 │
              ┌───────────▼──────┐ ┌────────▼─────────┐
              │ Cross-Document     │ │  Face Verification │
              │ Consistency Engine │ │  (pretrained,       │
              │ (2+ docs)          │ │  score + band)       │
              └───────────┬──────┘ └────────┬─────────┘
                          └────────┬─────────┘
                                   │  RiskSignal[] (canonical contract, Sec. 12)
                        ┌──────────▼──────────┐
                        │   Risk Engine         │
                        │  (rule-based,          │
                        │   weighted, config)     │
                        └──────────┬──────────┘
                                   │  RiskAssessment
                        ┌──────────▼──────────┐
                        │  Explainability Layer │
                        │  (evidence bundle +    │
                        │   visual overlays)      │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  PostgreSQL            │
                        │  cases · evidence ·     │
                        │  audit_log · users       │
                        └───────────────────────┘
```

Everything in this diagram is in the FINAL MVP (Section A). Nothing from Sections C or D appears here — if it's not on this diagram, it does not get built until this diagram is fully working end to end.

---

*End of Architecture Decision Review v1. This document supersedes the Project Bible wherever the two disagree. Next phase: implementation, starting at Section 13, Step 1.*
