import { useState } from "react";
import {
  ShieldCheck,
  Upload,
  FileImage,
  ArrowRight,
  LockKeyhole,
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import api from "./api";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [screen, setScreen] = useState("upload");

  const [caseId, setCaseId] = useState(null);
  const [documentId, setDocumentId] = useState(null);
  const [results, setResults] = useState(null);

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    if (file) {
      setSelectedFile(file);
    }
  };

  const handleBeginVerification = async () => {
    if (!selectedFile) return;

    try {
      setScreen("processing");

      // 1. Create screening case
      const caseResponse = await api.post("/cases/", {
        subject_name: "Unknown Passenger",
      });

      const newCaseId = caseResponse.data.id;
      setCaseId(newCaseId);

      console.log("Created case:", newCaseId);

      // 2. Upload passport
      const formData = new FormData();

      formData.append("doc_type", "passport");
      formData.append("file", selectedFile);

      const documentResponse = await api.post(
        `/cases/${newCaseId}/documents`,
        formData
      );

      const newDocumentId = documentResponse.data.id;
      setDocumentId(newDocumentId);

      console.log("Uploaded document:", newDocumentId);
      console.log("Passport successfully sent to backend.");

      // 3. Run OCR, MRZ and document forensics
      console.log("Starting document analysis...");

      const [ocrResponse, mrzResponse, forensicsResponse] =
        await Promise.all([
          api.post(`/documents/${newDocumentId}/ocr`),
          api.post(`/documents/${newDocumentId}/mrz`),
          api.post(`/documents/${newDocumentId}/forensics`),
        ]);

      console.log("OCR completed:", ocrResponse.data);
      console.log("MRZ completed:", mrzResponse.data);
      console.log("Forensics completed:", forensicsResponse.data);

      // 4. Face verification
      console.log("Starting face verification...");

      const faceResponse = await api.post(
        `/cases/${newCaseId}/face-verification`,
        {
          document_id: newDocumentId,
          probe_face_path: "/app/data/passports/passport_genuine.png",
        }
      );

      console.log("Face verification completed:", faceResponse.data);

      // 5. Risk assessment
      console.log("Starting risk assessment...");

      const riskResponse = await api.post(
        `/cases/${newCaseId}/risk-assessment`
      );

      console.log("Risk assessment completed:", riskResponse.data);

      // 6. Fetch complete results
      console.log("Fetching complete verification results...");

      const fullResponse = await api.get(
        `/cases/${newCaseId}/full`
      );

      console.log(
        "Complete verification results:",
        fullResponse.data
      );

      // Save results
      setResults(fullResponse.data);

      // Move to results screen
      setScreen("results");

    } catch (error) {
      console.error("Verification failed:", error);

      setScreen("upload");

      alert(
        error.response?.data?.detail ||
          "Could not connect to the VERIFAI backend."
      );
    }
  };

  // ============================================================
  // PROCESSING SCREEN
  // ============================================================

  if (screen === "processing") {
    return (
      <div className="app">
        <header className="topbar">
          <div className="brand">
            <div className="brand-icon">
              <ShieldCheck size={24} />
            </div>

            <div>
              <div className="brand-name">VERIFAI</div>
              <div className="brand-subtitle">
                Identity Risk Screening
              </div>
            </div>
          </div>

          <div className="system-status">
            <span className="status-dot"></span>
            SYSTEM ONLINE
          </div>
        </header>

        <main className="processing-page">
          <div className="page-label">DOCUMENT ANALYSIS</div>

          <h1>Verifying passenger</h1>

          <p className="intro">
            VERIFAI is analyzing the submitted document and running
            identity verification checks.
          </p>

          <section className="processing-card">
            <div className="processing-top">
              <div className="processing-spinner"></div>

              <div>
                <h2>Analysis in progress</h2>

                <p>
                  Please wait while all verification modules complete.
                </p>
              </div>
            </div>

            <div className="analysis-list">

              <div className="analysis-item active">
                <div className="analysis-icon">01</div>

                <div className="analysis-content">
                  <strong>OCR</strong>
                  <span>
                    Extracting passport information
                  </span>
                </div>

                <div className="analysis-status">
                  PROCESSING
                </div>
              </div>

              <div className="analysis-item">
                <div className="analysis-icon">02</div>

                <div className="analysis-content">
                  <strong>MRZ VALIDATION</strong>
                  <span>
                    Checking machine-readable zone
                  </span>
                </div>

                <div className="analysis-status">
                  WAITING
                </div>
              </div>

              <div className="analysis-item">
                <div className="analysis-icon">03</div>

                <div className="analysis-content">
                  <strong>DOCUMENT FORENSICS</strong>
                  <span>
                    Analyzing potential manipulation
                  </span>
                </div>

                <div className="analysis-status">
                  WAITING
                </div>
              </div>

              <div className="analysis-item">
                <div className="analysis-icon">04</div>

                <div className="analysis-content">
                  <strong>FACE VERIFICATION</strong>
                  <span>
                    Comparing identity features
                  </span>
                </div>

                <div className="analysis-status">
                  WAITING
                </div>
              </div>

              <div className="analysis-item">
                <div className="analysis-icon">05</div>

                <div className="analysis-content">
                  <strong>RISK ASSESSMENT</strong>
                  <span>
                    Calculating overall risk
                  </span>
                </div>

                <div className="analysis-status">
                  WAITING
                </div>
              </div>

            </div>

            <div className="processing-security">
              <LockKeyhole size={16} />

              <span>
                Processing is performed through the secure VERIFAI
                analysis pipeline.
              </span>
            </div>
          </section>

          <p className="disclaimer">
            Do not close this window while document analysis is in progress.
          </p>
        </main>
      </div>
    );
  }

  // ============================================================
  // RESULTS SCREEN
  // ============================================================

  if (screen === "results") {
    const riskScore =
      results?.risk_assessment?.overall_score ?? "—";

    const riskBand =
      results?.risk_assessment?.risk_band ?? "REVIEW"; 

    return (
      <div className="app">

        <header className="topbar">
          <div className="brand">
            <div className="brand-icon">
              <ShieldCheck size={24} />
            </div>

            <div>
              <div className="brand-name">VERIFAI</div>
              <div className="brand-subtitle">
                Identity Risk Screening
              </div>
            </div>
          </div>

          <div className="system-status">
            <span className="status-dot"></span>
            SYSTEM ONLINE
          </div>
        </header>

        <main className="results-page">

          <div className="page-label">
            VERIFICATION COMPLETE
          </div>

          <h1>Passenger verification results</h1>

          <p className="intro">
            AI-assisted verification has completed. Review the
            available evidence before making the final decision.
          </p>

          {/* CASE INFORMATION */}

          <section className="results-card">

            <div className="results-header">

              <div>
                <span className="result-label">
                  CASE ID
                </span>

                <strong className="case-id">
                  {caseId || "—"}
                </strong>
              </div>

              <div className="result-complete">
                <CheckCircle2 size={20} />
                ANALYSIS COMPLETE
              </div>

            </div>

            {/* RISK */}

            <div className="risk-section">

              <div>
                <span className="result-label">
                  OVERALL RISK
                </span>

                <div className="risk-score">
                  <strong>{riskScore}</strong>
                  <span>/ 100</span>
                </div>
              </div>

              <div className="risk-band">
                {String(riskBand).toUpperCase()}
              </div>

            </div>

            {/* MODULE RESULTS */}

            <div className="verification-grid">

              <div className="verification-item">
                <div className="verification-title">
                  <CheckCircle2 size={18} />
                  OCR
                </div>

                <strong>COMPLETED</strong>
              </div>

              <div className="verification-item">
                <div className="verification-title">
                  <CheckCircle2 size={18} />
                  MRZ
                </div>

                <strong>COMPLETED</strong>
              </div>

              <div className="verification-item">
                <div className="verification-title">
                  <CheckCircle2 size={18} />
                  FORENSICS
                </div>

                <strong>COMPLETED</strong>
              </div>

              <div className="verification-item">
                <div className="verification-title">
                  <CheckCircle2 size={18} />
                  FACE
                </div>

                <strong>COMPLETED</strong>
              </div>

            </div>

          </section>

          {/* EVIDENCE */}

          <section className="evidence-card">

            <div className="page-label">
              AI EVIDENCE
            </div>

            <h2>Verification summary</h2>

            <p>
              The verification pipeline has completed OCR,
              MRZ validation, document forensics, face verification,
              and risk assessment.
            </p>

            <div className="evidence-warning">
              <AlertTriangle size={20} />

              <span>
                AI results are decision-support evidence and should
                be reviewed by an authorized officer.
              </span>
            </div>

          </section>

          {/* OFFICER DECISION */}

          <section className="decision-card">

            <div>
              <div className="page-label">
                OFFICER DECISION
              </div>

              <h2>Review and decide</h2>

              <p>
                VERIFAI provides evidence and risk assessment.
                The final passenger decision remains with the
                authorized officer.
              </p>
            </div>

            <div className="decision-buttons">

              <button className="decision-button approve">
                APPROVE
              </button>

              <button className="decision-button escalate">
                ESCALATE
              </button>

              <button className="decision-button reject">
                REJECT
              </button>

            </div>

          </section>

          {/* NEW SCREENING */}

          <button
            className="new-screening-button"
            onClick={() => {
              setSelectedFile(null);
              setResults(null);
              setCaseId(null);
              setDocumentId(null);
              setScreen("upload");
            }}
          >
            Start new screening
          </button>

          <p className="disclaimer">
            Final decisions must be made by an authorized human officer.
          </p>

        </main>
      </div>
    );
  }

  // ============================================================
  // UPLOAD SCREEN
  // ============================================================

  return (
    <div className="app">

      <header className="topbar">

        <div className="brand">

          <div className="brand-icon">
            <ShieldCheck size={24} />
          </div>

          <div>
            <div className="brand-name">
              VERIFAI
            </div>

            <div className="brand-subtitle">
              Identity Risk Screening
            </div>
          </div>

        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          SYSTEM ONLINE
        </div>

      </header>

      <main className="main-content">

        <div className="page-label">
          CHECKPOINT SCREENING
        </div>

        <h1>Verify a passenger</h1>

        <p className="intro">
          Upload a passport document to begin AI-assisted identity
          verification and risk assessment.
        </p>

        {/* UPLOAD CARD */}

        <section className="upload-card">

          <div className="upload-icon">
            <Upload size={30} />
          </div>

          <h2>
            Upload passport image
          </h2>

          <p className="upload-description">
            Provide a clear image of the passport identity page.
          </p>

          <label className="upload-area">

            <input
              type="file"
              accept="image/*"
              onChange={handleFileChange}
            />

            <FileImage size={34} />

            <span className="upload-title">
              {selectedFile
                ? selectedFile.name
                : "Choose passport image"}
            </span>

            <span className="upload-hint">
              PNG, JPG or JPEG
            </span>

          </label>

          {selectedFile && (
            <div className="selected-file">

              <div>
                <strong>
                  Selected document
                </strong>

                <span>
                  {selectedFile.name}
                </span>
              </div>

              <span className="file-ready">
                READY
              </span>

            </div>
          )}

          <button
            className="continue-button"
            disabled={!selectedFile}
            onClick={handleBeginVerification}
          >
            Begin verification
            <ArrowRight size={18} />
          </button>

        </section>

        {/* AI INFORMATION */}

        <section className="process-info">

          <div className="process-header">
            <LockKeyhole size={18} />
            <span>
              SECURE AI-ASSISTED SCREENING
            </span>
          </div>

          <div className="process-grid">

            <div>
              <strong>OCR</strong>
              <span>
                Document text extraction
              </span>
            </div>

            <div>
              <strong>MRZ</strong>
              <span>
                Machine-readable zone validation
              </span>
            </div>

            <div>
              <strong>FORENSICS</strong>
              <span>
                Document manipulation analysis
              </span>
            </div>

            <div>
              <strong>FACE</strong>
              <span>
                Identity verification
              </span>
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

export default App;