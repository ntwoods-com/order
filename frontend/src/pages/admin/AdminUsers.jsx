import React from "react";
import * as api from "../../api/client.js";

export default function AdminUsers() {
  const [rows, setRows] = React.useState([]);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      setError("");
      try {
        const res = await api.adminUsers();
        if (!cancelled) setRows(res?.data || []);
      } catch (e) {
        if (!cancelled) setError(e?.message || "Failed to load users");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Admin - Users</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Users are configured via backend env vars (USER1/USER2... + ADMIN_USERS).
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        {rows.length ? (
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u) => (
                <tr key={u.username}>
                  <td>{u.username}</td>
                  <td>{u.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="muted">No users found.</div>
        )}
      </div>
    </div>
  );
}

