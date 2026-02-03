import React from "react";
import * as api from "../../api/client.js";

export default function AdminLogs() {
  const [lines, setLines] = React.useState(500);
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function load() {
    setBusy(true);
    setError("");
    try {
      const res = await api.adminLogs(lines);
      setData(res?.data || null);
    } catch (e) {
      setError(e?.message || "Failed to load logs");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    void load();
  }, []);

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Admin - Logs</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Reads from backend log file (if enabled).
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        <div className="row" style={{ alignItems: "flex-end" }}>
          <div style={{ width: 160 }}>
            <div className="field" style={{ marginBottom: 0 }}>
              <label>Lines</label>
              <input value={lines} onChange={(e) => setLines(Number(e.target.value || 0))} />
            </div>
          </div>
          <button className="btn btn-primary" onClick={load} disabled={busy}>
            {busy ? "Loading..." : "Reload"}
          </button>
        </div>
        <div style={{ height: 12 }} />
        {data ? (
          <>
            <div className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
              File: <code>{data.file}</code>
            </div>
            <div className="codeblock">{(data.lines || []).join("\n")}</div>
          </>
        ) : (
          <div className="muted">No data.</div>
        )}
      </div>
    </div>
  );
}

