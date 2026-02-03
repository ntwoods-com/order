import React from "react";
import * as api from "../api/client.js";

export default function Search() {
  const [q, setQ] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [results, setResults] = React.useState([]);

  async function onSearch(e) {
    e.preventDefault();
    const query = q.trim();
    if (query.length < 2) {
      setError("Type at least 2 characters");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const res = await api.searchOrders(query);
      setResults(res?.results || []);
    } catch (e2) {
      setError(e2?.message || "Search failed");
      setResults([]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Search Orders</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Search by dealer, city, order ID, username.
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        <form onSubmit={onSearch} className="row" style={{ alignItems: "flex-end" }}>
          <div className="col" style={{ minWidth: 320 }}>
            <div className="field">
              <label>Query</label>
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Mumbai / dealer / 02-26-00010" />
            </div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <button className="btn btn-primary" disabled={busy}>
              {busy ? "Searching..." : "Search"}
            </button>
          </div>
        </form>

        <div style={{ height: 14 }} />

        {results.length ? (
          <table>
            <thead>
              <tr>
                <th>Order ID</th>
                <th>Dealer</th>
                <th>City</th>
                <th>User</th>
                <th>Generated</th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id}>
                  <td>{r.order_id}</td>
                  <td>{r.dealer_name}</td>
                  <td>{r.city}</td>
                  <td>{r.username}</td>
                  <td>{r.generated_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="muted">{busy ? "" : "No results."}</div>
        )}
      </div>
    </div>
  );
}

