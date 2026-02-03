import React from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client.js";

const UPLOAD_KEY = "sale_order_upload_additional";

export function getAdditionalUploadState() {
  try {
    return JSON.parse(sessionStorage.getItem(UPLOAD_KEY) || "null");
  } catch {
    return null;
  }
}

export function setAdditionalUploadState(state) {
  sessionStorage.setItem(UPLOAD_KEY, JSON.stringify(state));
}

export default function AdditionalUpload() {
  const navigate = useNavigate();
  const [file, setFile] = React.useState(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function onUpload() {
    if (!file) return;
    setError("");
    setBusy(true);
    try {
      const res = await api.uploadExcel(file);
      setAdditionalUploadState(res?.data || null);
      navigate("/additional/details");
    } catch (e) {
      setError(e?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Additional Order - Upload Excel</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Generates a report using an existing Order ID.
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        <div className="field">
          <label>Excel File</label>
          <input type="file" accept=".xls,.xlsx" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <p className="muted" style={{ margin: "8px 0 0 0", fontSize: 13 }}>
            {file ? `Selected: ${file.name} (${Math.round(file.size / 1024)} KB)` : "No file selected"}
          </p>
        </div>
        <button className="btn btn-primary" onClick={onUpload} disabled={!file || busy}>
          {busy ? "Uploading..." : "Upload & Continue"}
        </button>
      </div>
    </div>
  );
}

