import { useState, useRef } from "react";
import {
  ShieldCheck,
  Upload,
  FileImage,
  ArrowRight,
  LockKeyhole,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Eye,
  UserCheck,
  FileText,
  ScanLine,
  ShieldAlert,
  Fingerprint,
  ArrowLeft,
} from "lucide-react";
import api from "./api";
import "./App.css";

/* ================================================================
   VERIFAI — Complete Frontend Dashboard
   ================================================================
   3 Screens:
   1. Upload    → Officer uploads passport image
   2. Processing → Shows live progress of 5 AI modules
   3. Results   → Full dashboard with data, signals, and decision
   ================================================================ */

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [probeFile, setProbeFile] = useState(null);
  const [probePreviewUrl, setProbePreviewUrl] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [screen, setScreen] = useState("upload");

  const [caseId, setCaseId] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [results, setResults] = useState(null);
  const [decisionMade, setDecisionMade] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Processing step tracker
  const [steps, setSteps] = useState([
    { name: "OCR", desc: "Extracting passport text", status: "waiting" },
    { name: "MRZ", desc: "Validating machine-readable zone", status: "waiting" },
    { name: "FORENSICS", desc: "Detecting document tampering", status: "waiting" },
    { name: "FACE", desc: "Comparing identity photos", status: "waiting" },
    { name: "RISK", desc: "Calculating overall risk score", status: "waiting" },
  ]);

  const fileInputRef = useRef(null);
  const probeInputRef = useRef(null);

  const updateStep = (index, status) => {
    setSteps((prev) => prev.map((s, i) => (i === index ? { ...s, status } : s)));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };


  const handleProbeFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setProbeFile(file);
      setProbePreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      setSelectedFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const resetAll = () => {
    setProbeFile(null);
    setProbePreviewUrl(null);
    setSelectedFile(null);
    setPreviewUrl(null);
    setResults(null);
    setCaseId(null);
    setDocumentId(null);
    setDecisionMade(null);
    setErrorMsg(null);
    setSteps([
      { name: "OCR", desc: "Extracting passport text", status: "waiting" },
      { name: "MRZ", desc: "Validating machine-readable zone", status: "waiting" },
      { name: "FORENSICS", desc: "Detecting document tampering", status: "waiting" },
      { name: "FACE", desc: "Comparing identity photos", status: "waiting" },
      { name: "RISK", desc: "Calculating overall risk score", status: "waiting" },
    ]);
    setScreen("upload");
  };

  // ================================================================
  // THE MAIN PIPELINE — calls all backend endpoints in order
  // ================================================================
  const handleBeginVerification = async () => {
    if (!selectedFile || !probeFile) { setErrorMsg("Please upload both a passport and a selfie."); return; }
    setScreen("processing");
    setErrorMsg(null);

    try {
      // Step 0: Create case
      const caseRes = await api.post("/cases/", { subject_name: "Unknown Passenger" });
      const newCaseId = caseRes.data.id;
      setCaseId(newCaseId);


      // Step 0b: Upload document
      const formData = new FormData();
      formData.append("doc_type", "passport");
      formData.append("file", selectedFile);
      const docRes = await api.post(`/cases/${newCaseId}/documents`, formData);
      const newDocId = docRes.data.id;
      setDocumentId(newDocId);

      // Step 0c: Upload probe image
      const probeFormData = new FormData();
      probeFormData.append("doc_type", "probe_face");
      probeFormData.append("file", probeFile);
      const probeRes = await api.post(`/cases/${newCaseId}/documents`, probeFormData);
      const uploadedProbePath = probeRes.data.image_path;


      // Step 1: OCR
      updateStep(0, "active");
      try {
        await api.post(`/documents/${newDocId}/ocr`);
        updateStep(0, "done");
      } catch {
        updateStep(0, "error");
      }

      // Step 2: MRZ
      updateStep(1, "active");
      try {
        await api.post(`/documents/${newDocId}/mrz`);
        updateStep(1, "done");
      } catch {
        updateStep(1, "error");
      }

      // Step 3: Forensics
      updateStep(2, "active");
      try {
        await api.post(`/documents/${newDocId}/forensics`);
        updateStep(2, "done");
      } catch {
        updateStep(2, "error");
      }

      // Step 4: Face verification
      updateStep(3, "active");
      try {
        await api.post(`/cases/${newCaseId}/face-verification`, {
          document_id: newDocId,
          probe_face_path: uploadedProbePath,
        });
        updateStep(3, "done");
      } catch {
        updateStep(3, "error");
      }

      // Step 5: Risk assessment
      updateStep(4, "active");
      try {
        await api.post(`/cases/${newCaseId}/risk-assessment`);
        updateStep(4, "done");
      } catch {
        updateStep(4, "error");
      }

      // Fetch complete results
      const fullRes = await api.get(`/cases/${newCaseId}/full`);
      setResults(fullRes.data);
      setScreen("results");
    } catch (error) {
      console.error("Pipeline error:", error);
      setErrorMsg(
        error.response?.data?.detail ||
          "Could not connect to the VERIFAI backend. Make sure it is running on port 8000."
      );
      setScreen("upload");
    }
  };

  // ================================================================
  // DECISION HANDLER
  // ================================================================
  const handleDecision = async (decision) => {
    try {
      await api.post(`/cases/${caseId}/decision`, {
        decision,
        decision_notes: `Officer ${decision}d via VERIFAI dashboard`,
      });
      setDecisionMade(decision);
    } catch (error) {
      alert("Failed to submit decision: " + (error.response?.data?.detail || error.message));
    }
  };

  // ================================================================
  // HELPERS
  // ================================================================
  const riskColor = (band) => {
    if (!band) return "#94a3b8";
    const b = band.toLowerCase();
    if (b === "low") return "#22c55e";
    if (b === "medium") return "#eab308";
    return "#ef4444";
  };

  const riskBg = (band) => {
    if (!band) return "rgba(148,163,184,0.1)";
    const b = band.toLowerCase();
    if (b === "low") return "rgba(34,197,94,0.1)";
    if (b === "medium") return "rgba(234,179,8,0.1)";
    return "rgba(239,68,68,0.1)";
  };

  const stepIcon = (status) => {
    if (status === "done") return <CheckCircle2 size={18} className="step-icon done" />;
    if (status === "error") return <XCircle size={18} className="step-icon error" />;
    if (status === "active") return <div className="mini-spinner" />;
    return <div className="step-dot" />;
  };

  // ================================================================
  // SCREEN: PROCESSING
  // ================================================================
  if (screen === "processing") {
    return (
      <div className="app">
        <Header />
        <main className="page-container">
          <div className="page-label">DOCUMENT ANALYSIS</div>
          <h1>Analyzing document</h1>
          <p className="intro">
            VERIFAI is running 5 AI verification modules on the uploaded document.
            This may take a moment.
          </p>

          <section className="card">
            <div className="processing-top">
              <div className="processing-spinner" />
              <div>
                <h2>Analysis in progress</h2>
                <p className="muted">Please wait while all modules complete.</p>
              </div>
            </div>

            <div className="steps-list">
              {steps.map((step, i) => (
                <div key={i} className={`step-row ${step.status}`}>
                  <div className="step-num">{String(i + 1).padStart(2, "0")}</div>
                  <div className="step-info">
                    <strong>{step.name}</strong>
                    <span>{step.desc}</span>
                  </div>
                  <div className="step-status-badge">
                    {stepIcon(step.status)}
                    <span>{step.status === "active" ? "PROCESSING" : step.status.toUpperCase()}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="security-note">
              <LockKeyhole size={16} />
              <span>All processing is performed through the secure VERIFAI pipeline.</span>
            </div>
          </section>

          <p className="disclaimer">Do not close this window during analysis.</p>
        </main>
      </div>
    );
  }

  // ================================================================
  // SCREEN: RESULTS
  // ================================================================
  if (screen === "results" && results) {
    const risk = results.risk_assessment;
    const ocr = results.ocr;
    const mrz = results.mrz;
    const forensics = results.forensics;
    const face = results.face_verification;
    const score = risk?.overall_score ?? 0;
    const band = risk?.risk_band ?? "unknown";
    const signals = risk?.signals ?? [];

    return (
      <div className="app">
        <Header />
        <main className="page-container">
          <div className="page-label">VERIFICATION COMPLETE</div>
          <h1>Screening results</h1>
          <p className="intro">
            Review the AI evidence below, then submit your officer decision.
          </p>

          {/* ── RISK SCORE HERO ─────────────────────────────── */}
          <section className="card risk-hero" style={{ borderColor: riskColor(band) + "33" }}>
            <div className="risk-hero-top">
              <div>
                <span className="result-label">CASE ID</span>
                <strong className="case-id-text">{caseId?.slice(0, 8)}...</strong>
              </div>
              <div
                className="risk-badge"
                style={{ background: riskBg(band), color: riskColor(band) }}
              >
                <ShieldAlert size={16} />
                {band.toUpperCase()} RISK
              </div>
            </div>

            <div className="risk-score-display">
              <div className="risk-number" style={{ color: riskColor(band) }}>
                {score != null ? Number(score).toFixed(1) : "—"}
              </div>
              <div className="risk-out-of">/ 100</div>
            </div>

            <div className="risk-bar-track">
              <div
                className="risk-bar-fill"
                style={{ width: `${Math.min(score, 100)}%`, background: riskColor(band) }}
              />
            </div>
            <div className="risk-bar-labels">
              <span>0 — Low</span>
              <span>50 — Medium</span>
              <span>100 — High</span>
            </div>
          </section>

          {/* ── MODULE RESULTS GRID ────────────────────────── */}
          <div className="modules-grid">
            {/* OCR */}
            <section className="card module-card">
              <div className="module-header">
                <FileText size={18} />
                <strong>OCR — Text Extraction</strong>
              </div>
              {ocr?.structured_fields && Object.keys(ocr.structured_fields).length > 0 ? (
                <div className="field-list">
                  {Object.entries(ocr.structured_fields).map(([key, val]) => (
                    <div key={key} className="field-row">
                      <span className="field-key">{key.replace(/_/g, " ")}</span>
                      <span className="field-val">{val || "—"}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted">No visual text fields extracted</p>
              )}
            </section>

            {/* MRZ */}
            <section className="card module-card">
              <div className="module-header">
                <ScanLine size={18} />
                <strong>MRZ — Checksum Validation</strong>
              </div>
              <div className="mrz-result">
                {mrz?.checksum_valid === true ? (
                  <div className="mrz-badge pass">
                    <CheckCircle2 size={20} /> ALL CHECKSUMS VALID
                  </div>
                ) : mrz?.checksum_valid === false ? (
                  <div className="mrz-badge fail">
                    <XCircle size={20} /> CHECKSUM FAILED
                  </div>
                ) : (
                  <div className="mrz-badge neutral">
                    <AlertTriangle size={20} /> NO MRZ DATA
                  </div>
                )}
                {Array.isArray(mrz?.checksum_details) && mrz.checksum_details.length > 0 && (
                  <div
                    className="checksum-details-grid"
                    style={{
                      marginTop: 10,
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: "6px",
                      fontSize: "12px",
                    }}
                  >
                    {mrz.checksum_details.map((cd, idx) => (
                      <div key={idx} style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        {cd.valid ? (
                          <CheckCircle2 size={14} color="#22c55e" />
                        ) : (
                          <XCircle size={14} color="#ef4444" />
                        )}
                        <span style={{ color: cd.valid ? "#cbd5e1" : "#fca5a5" }}>
                          {cd.field?.replace(/_/g, " ")}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                {ocr?.structured_fields?.dob &&
                  mrz?.parsed_fields?.date_of_birth &&
                  ocr.structured_fields.dob !== mrz.parsed_fields.date_of_birth && (
                    <div
                      style={{
                        marginTop: 10,
                        padding: "8px 10px",
                        background: "rgba(239, 68, 68, 0.15)",
                        border: "1px solid rgba(239, 68, 68, 0.3)",
                        borderRadius: 6,
                        fontSize: "12px",
                        color: "#fca5a5",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                      }}
                    >
                      <AlertTriangle size={14} color="#ef4444" />
                      <span>
                        DOB Mismatch: Visual ({ocr.structured_fields.dob}) ≠ MRZ ({mrz.parsed_fields.date_of_birth})
                      </span>
                    </div>
                  )}
                {mrz?.parsed_fields && (
                  <div className="field-list" style={{ marginTop: 12 }}>
                    {Object.entries(mrz.parsed_fields).map(([k, v]) => (
                      <div key={k} className="field-row">
                        <span className="field-key">{k.replace(/_/g, " ")}</span>
                        <span className="field-val">{String(v)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            {/* FORENSICS */}
            <section className="card module-card">
              <div className="module-header">
                <Eye size={18} />
                <strong>Forensics — Tampering Detection</strong>
              </div>
              {forensics ? (
                <>
                  <div className="forensics-score">
                    <span className="result-label">MANIPULATION PROBABILITY</span>
                    <div
                      className="forensics-percent"
                      style={{
                        color:
                          (forensics.overall_manipulation_probability ?? 0) >= 0.7
                            ? "#ef4444"
                            : (forensics.overall_manipulation_probability ?? 0) >= 0.4
                            ? "#eab308"
                            : "#22c55e",
                      }}
                    >
                      {forensics.overall_manipulation_probability != null
                        ? `${(Number(forensics.overall_manipulation_probability) * 100).toFixed(0)}%`
                        : "—"}
                    </div>
                  </div>
                  <div className="field-list" style={{ marginTop: 8 }}>
                    <div className="field-row">
                      <span className="field-key">ELA Score</span>
                      <span className="field-val">
                        {forensics.ela_score != null ? Number(forensics.ela_score).toFixed(3) : "—"}
                      </span>
                    </div>
                    <div className="field-row">
                      <span className="field-key">Noise Score</span>
                      <span className="field-val">
                        {forensics.noise_inconsistency_score != null
                          ? Number(forensics.noise_inconsistency_score).toFixed(3)
                          : "—"}
                      </span>
                    </div>
                  </div>
                </>
              ) : (
                <p className="muted">No forensics data available</p>
              )}
            </section>

            {/* FACE */}
            <section className="card module-card">
              <div className="module-header">
                <Fingerprint size={18} />
                <strong>Face — Identity Verification</strong>
              </div>
              {face ? (
                <div className="face-result">
                  <div
                    className="face-badge"
                    style={{
                      background:
                        face.band === "match"
                          ? "rgba(34,197,94,0.1)"
                          : face.band === "uncertain"
                          ? "rgba(234,179,8,0.1)"
                          : "rgba(239,68,68,0.1)",
                      color:
                        face.band === "match"
                          ? "#22c55e"
                          : face.band === "uncertain"
                          ? "#eab308"
                          : "#ef4444",
                    }}
                  >
                    {face.band === "match" ? (
                      <UserCheck size={20} />
                    ) : (
                      <AlertTriangle size={20} />
                    )}
                    {face.band?.toUpperCase() || "UNKNOWN"}
                  </div>
                  <div className="field-list" style={{ marginTop: 12 }}>
                    <div className="field-row">
                      <span className="field-key">Similarity</span>
                      <span className="field-val">
                        {face.similarity_score != null
                          ? `${(Number(face.similarity_score) * 100).toFixed(1)}%`
                          : "—"}
                      </span>
                    </div>
                  </div>
                  {face.error_message && (
                    <p className="error-text">{face.error_message}</p>
                  )}
                </div>
              ) : (
                <p className="muted">No face verification data</p>
              )}
            </section>
          </div>

          {/* ── RISK SIGNALS ───────────────────────────────── */}
          {signals.length > 0 && (
            <section className="card">
              <div className="module-header" style={{ marginBottom: 16 }}>
                <AlertTriangle size={18} />
                <strong>Risk Signals — Why this score?</strong>
              </div>
              <div className="signals-list">
                {signals.map((sig, i) => (
                  <div
                    key={i}
                    className={`signal-card ${sig.direction === "increases_risk" ? "danger" : "safe"}`}
                  >
                    <div className="signal-top">
                      <span className="signal-source">
                        {sig.source_module?.toUpperCase()}
                      </span>
                      <span className="signal-name">{sig.signal_name?.replace(/_/g, " ")}</span>
                      <span
                        className="signal-dir"
                        style={{
                          color:
                            sig.direction === "increases_risk" ? "#ef4444" : "#22c55e",
                        }}
                      >
                        {sig.direction === "increases_risk" ? "▲ RISK" : "▼ SAFE"}
                      </span>
                    </div>
                    <p className="signal-explanation">{sig.explanation}</p>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ── EVIDENCE DISCLAIMER ────────────────────────── */}
          <section className="card disclaimer-card">
            <AlertTriangle size={20} className="warn-icon" />
            <p>
              AI results are <strong>decision-support evidence</strong> and must be
              reviewed by an authorized officer. The system does not make final
              decisions.
            </p>
          </section>

          {/* ── OFFICER DECISION ───────────────────────────── */}
          <section className="card decision-section">
            <div className="module-header" style={{ marginBottom: 8 }}>
              <ShieldCheck size={18} />
              <strong>Officer Decision</strong>
            </div>
            <p className="muted" style={{ marginBottom: 20 }}>
              Review the evidence above, then submit your final decision.
            </p>

            {decisionMade ? (
              <div
                className="decision-confirmation"
                style={{
                  background:
                    decisionMade === "approve"
                      ? "rgba(34,197,94,0.1)"
                      : decisionMade === "escalate"
                      ? "rgba(234,179,8,0.1)"
                      : "rgba(239,68,68,0.1)",
                  borderColor:
                    decisionMade === "approve"
                      ? "rgba(34,197,94,0.3)"
                      : decisionMade === "escalate"
                      ? "rgba(234,179,8,0.3)"
                      : "rgba(239,68,68,0.3)",
                }}
              >
                <CheckCircle2 size={22} />
                <span>
                  Decision recorded: <strong>{decisionMade.toUpperCase()}</strong>
                </span>
              </div>
            ) : (
              <div className="decision-buttons">
                <button className="decision-btn approve" onClick={() => handleDecision("approve")}>
                  <CheckCircle2 size={18} />
                  APPROVE
                </button>
                <button className="decision-btn escalate" onClick={() => handleDecision("escalate")}>
                  <AlertTriangle size={18} />
                  ESCALATE
                </button>
                <button className="decision-btn reject" onClick={() => handleDecision("reject")}>
                  <XCircle size={18} />
                  REJECT
                </button>
              </div>
            )}
          </section>

          {/* ── NEW SCREENING ──────────────────────────────── */}
          <button className="new-screening-btn" onClick={resetAll}>
            <ArrowLeft size={16} />
            Start new screening
          </button>

          <p className="disclaimer">
            Final decisions must be made by an authorized human officer.
          </p>
        </main>
      </div>
    );
  }

  // ================================================================
  // SCREEN: UPLOAD (DEFAULT)
  // ================================================================
  return (
    <div className="app">
      <Header />
      <main className="page-container">
        <div className="page-label">CHECKPOINT SCREENING</div>
        <h1>Verify a passenger</h1>
        <p className="intro">
          Upload a passport document to begin AI-assisted identity
          verification and risk assessment.
        </p>

        {errorMsg && (
          <div className="error-banner">
            <XCircle size={18} />
            <span>{errorMsg}</span>
            <button onClick={() => setErrorMsg(null)}>✕</button>
          </div>
        )}

        <section className="card upload-card">
          <div className="upload-icon-box">
            <Upload size={28} />
          </div>
          <h2>Upload passport image</h2>
          <p className="muted">Provide a clear image of the passport identity page.</p>

          <label
            className="drop-zone"
            style={{ marginBottom: '20px' }}
          >
            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
            />
            {previewUrl ? (
              <img src={previewUrl} alt="Passport Preview" className="preview-img" />
            ) : (
              <>
                <FileImage size={34} />
                <span className="drop-title">Choose passport image</span>
              </>
            )}
          </label>

          <h2>Upload live selfie (Probe)</h2>
          <p className="muted">Provide a clear selfie for face verification.</p>

          <label
            className="drop-zone"
          >
            <input
              type="file"
              accept="image/*"
              onChange={handleProbeFileChange}
            />
            {probePreviewUrl ? (
              <img src={probePreviewUrl} alt="Selfie Preview" className="preview-img" />
            ) : (
              <>
                <UserCheck size={34} />
                <span className="drop-title">Choose selfie image</span>
              </>
            )}
          </label>

          {(selectedFile || probeFile) && (
            <div className="selected-file" style={{ marginTop: '20px' }}>
              <div>
                <strong>Selected files</strong>
                <span>Passport: {selectedFile ? "Ready" : "Missing"} | Selfie: {probeFile ? "Ready" : "Missing"}</span>
              </div>
            </div>
          )}

          <button
            className="primary-btn"
            disabled={!selectedFile || !probeFile}
            onClick={handleBeginVerification}
          >
            Begin verification
            <ArrowRight size={18} />
          </button>
        </section>

        <section className="card info-card">
          <div className="info-header">
            <LockKeyhole size={16} />
            <span>SECURE AI-ASSISTED SCREENING</span>
          </div>
          <div className="info-grid">
            <div>
              <strong>OCR</strong>
              <span>Text extraction</span>
            </div>
            <div>
              <strong>MRZ</strong>
              <span>Checksum validation</span>
            </div>
            <div>
              <strong>FORENSICS</strong>
              <span>Tampering detection</span>
            </div>
            <div>
              <strong>FACE</strong>
              <span>Identity matching</span>
            </div>
          </div>
        </section>

        <p className="disclaimer">
          VERIFAI provides decision support. Final passenger decisions
          remain with the authorized officer.
        </p>
      </main>
    </div>
  );
}

/* ── Shared header component ────────────────────────────────────── */
function Header() {
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-icon">
          <ShieldCheck size={22} />
        </div>
        <div>
          <div className="brand-name">VERIFAI</div>
          <div className="brand-sub">Identity Risk Screening</div>
        </div>
      </div>
      <div className="system-status">
        <span className="status-dot" />
        SYSTEM ONLINE
      </div>
    </header>
  );
}

export default App;