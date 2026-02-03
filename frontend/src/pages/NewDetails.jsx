import React from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client.js";
import { triggerDownload } from "../components/download.js";
import { getNewUploadState, setNewUploadState } from "./NewUpload.jsx";

export default function NewDetails() {
  const navigate = useNavigate();
  const upload = getNewUploadState();

  const [dealerName, setDealerName] = React.useState("");
  const [city, setCity] = React.useState("");
  const [orderDate, setOrderDate] = React.useState(() => new Date().toISOString().slice(0, 10));
  const [freight, setFreight] = React.useState("");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState(null);

  React.useEffect(() => {
    if (!upload?.upload_id) navigate("/new/upload", { replace: true });
  }, [upload, navigate]);

  async function onGenerate(e) {
    e.preventDefault();
    if (!upload?.upload_id) return;
    setError("");
    setBusy(true);
    try {
      const res = await api.generateReport({
        upload_id: upload.upload_id,
        dealer_name: dealerName,
        city,
        order_date: orderDate,
        freight_condition: freight,
        is_additional_order: false,
      });
      setResult(res?.data || null);
      setNewUploadState(null);
    } catch (e2) {
      setError(e2?.message || "Failed to generate report");
    } finally {
      setBusy(false);
    }
  }

  async function onDownload() {
    if (!result?.report_name) return;
    const blob = await api.downloadReportBlob(result.report_name);
    triggerDownload(blob, result.report_name);
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>New Order - Details</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          File: <code>{upload?.filename}</code>
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        {result ? (
          <div className="alert alert-success">
            <div style={{ fontWeight: 800, marginBottom: 6 }}>Report generated</div>
            <div className="muted" style={{ fontSize: 13 }}>
              Order ID: <code>{result.order_id}</code>
              <br />
              Report: <code>{result.report_name}</code>
            </div>
            <div style={{ height: 12 }} />
            <div className="row">
              <button className="btn btn-primary" onClick={onDownload}>
                Download
              </button>
              <button className="btn" onClick={() => navigate("/orders")}>
                Go to My Orders
              </button>
              <button className="btn" onClick={() => navigate("/new/upload")}>
                Create Another
              </button>
            </div>
          </div>
        ) : (
          <form onSubmit={onGenerate}>
            <div className="row">
              <div className="col">
                <div className="field">
                  <label>Dealer Name *</label>
                  <input value={dealerName} onChange={(e) => setDealerName(e.target.value)} required />
                </div>
              </div>
              <div className="col">
                <div className="field">
                  <label>City *</label>
                  <input value={city} onChange={(e) => setCity(e.target.value)} required />
                </div>
              </div>
            </div>
            <div className="row">
              <div className="col">
                <div className="field">
                  <label>Order Date *</label>
                  <input type="date" value={orderDate} onChange={(e) => setOrderDate(e.target.value)} required />
                </div>
              </div>
              <div className="col">
                <div className="field">
                  <label>Freight Condition</label>
                  <input value={freight} onChange={(e) => setFreight(e.target.value)} placeholder="e.g. FOB" />
                </div>
              </div>
            </div>
            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Generating..." : "Generate Report"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

