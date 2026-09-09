import re

with open("frontend/src/App.jsx", "r") as f:
    content = f.read()

# Add probeFile state
content = content.replace(
    'const [selectedFile, setSelectedFile] = useState(null);',
    'const [selectedFile, setSelectedFile] = useState(null);\n  const [probeFile, setProbeFile] = useState(null);\n  const [probePreviewUrl, setProbePreviewUrl] = useState(null);'
)

content = content.replace(
    'const fileInputRef = useRef(null);',
    'const fileInputRef = useRef(null);\n  const probeInputRef = useRef(null);'
)

content = content.replace(
    'const resetAll = () => {',
    'const resetAll = () => {\n    setProbeFile(null);\n    setProbePreviewUrl(null);'
)

# Handle probe file change
handle_file_str = """
  const handleProbeFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setProbeFile(file);
      setProbePreviewUrl(URL.createObjectURL(file));
    }
  };
"""
content = content.replace('  const handleDrop = (e) => {', handle_file_str + '\n  const handleDrop = (e) => {')

# Prevent verification if no probe
content = content.replace(
    'if (!selectedFile) return;',
    'if (!selectedFile || !probeFile) { setErrorMsg("Please upload both a passport and a selfie."); return; }'
)

# Upload probe and pass actual path
pipeline_upload_str = """
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
"""
content = content.replace(
"""      // Step 0b: Upload document
      const formData = new FormData();
      formData.append("doc_type", "passport");
      formData.append("file", selectedFile);
      const docRes = await api.post(`/cases/${newCaseId}/documents`, formData);
      const newDocId = docRes.data.id;
      setDocumentId(newDocId);""",
pipeline_upload_str
)

face_call_str = """        await api.post(`/cases/${newCaseId}/face-verification`, {
          document_id: newDocId,
          probe_face_path: uploadedProbePath,
        });"""
content = content.replace(
"""        await api.post(`/cases/${newCaseId}/face-verification`, {
          document_id: newDocId,
          probe_face_path: "../data/passports/passport_genuine.png",
        });""",
face_call_str
)

upload_ui_str = """
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
"""

import re
# Replace from <section className="card upload-card"> down to </section> before <section className="card info-card">
pattern = re.compile(r'<section className="card upload-card">.*?</section>', re.DOTALL)
content = pattern.sub(upload_ui_str.strip(), content)

with open("frontend/src/App.jsx", "w") as f:
    f.write(content)
