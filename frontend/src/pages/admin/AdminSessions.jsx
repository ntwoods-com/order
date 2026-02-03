import React from "react";
import * as api from "../../api/client.js";

export default function AdminSessions() {
  const [rows, setRows] = React.useState([]);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function load() {
    setBusy(true);
    setError("");
    try {
      const res = await api.adminSessions();
      setRows(res?.data || []);
    } catch (e) {
      setError(e?.message || "Failed to load sessions");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    void load();
  }, []);

  async function revoke(username) {
    setBusy(true);
    setError("");
    try {
      await api.adminRevokeSession(username);
      await load();
    } catch (e) {
      setError(e?.message || "Failed to revoke");
    } finally {
      setBusy(false);
    }
  }

  async function revokeAll() {
    setBusy(true);
    setError("");
    try {
      await api.adminRevokeAllSessions();
      await load();
    } catch (e) {
      setError(e?.message || "Failed to revoke all");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Admin - Sessions</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Revoke sessions to force re-login
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        <div className="row">
          <button className="btn btn-danger" onClick={revokeAll} disabled={busy}>
            Revoke All
          </button>
          <button className="btn" onClick={load} disabled={busy}>
            Refresh
          </button>
        </div>
        <div style={{ height: 12 }} />
        {rows.length ? (
          <table>
            <thead>
              <tr>
                <th>User</th>
                <th>IP</th>
                <th>Issued</th>
                <th>User Agent</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.username}>
                  <td>{s.username}</td>
                  <td>{s.ip || "-"}</td>
                  <td>{s.issued_at || "-"}</td>
                  <td style={{ fontSize: 12 }}>{s.user_agent || "-"}</td>
                  <td style={{ whiteSpace: "nowrap" }}>
                    <button className="btn btn-danger" onClick={() => revoke(s.username)} disabled={busy}>
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="muted">{busy ? "Loading..." : "No sessions."}</div>
        )}
      </div>
    </div>
  );
}

