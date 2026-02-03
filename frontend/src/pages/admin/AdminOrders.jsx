import React from "react";
import * as api from "../../api/client.js";
import { triggerDownload } from "../../components/download.js";

export default function AdminOrders() {
  const [rows, setRows] = React.useState([]);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [filters, setFilters] = React.useState({
    username: "",
    dealer_name: "",
    city: "",
    order_id: "",
  });
  const [page, setPage] = React.useState(1);

  async function load(p = page) {
    setBusy(true);
    setError("");
    try {
      const res = await api.adminOrders({ page: String(p), per_page: "25", ...filters });
      setRows(res?.data?.orders || []);
    } catch (e) {
      setError(e?.message || "Failed to load orders");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    void load(page);
  }, [page]);

  async function onDownload(reportName) {
    try {
      const blob = await api.downloadReportBlob(reportName);
      triggerDownload(blob, reportName);
    } catch (e) {
      setError(e?.message || "Download failed");
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Admin - Orders</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Search/filter all orders
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            void load(1);
          }}
        >
          <div className="row">
            <div className="col">
              <div className="field">
                <label>Username</label>
                <input value={filters.username} onChange={(e) => setFilters((s) => ({ ...s, username: e.target.value }))} />
              </div>
            </div>
            <div className="col">
              <div className="field">
                <label>Dealer</label>
                <input
                  value={filters.dealer_name}
                  onChange={(e) => setFilters((s) => ({ ...s, dealer_name: e.target.value }))}
                />
              </div>
            </div>
            <div className="col">
              <div className="field">
                <label>City</label>
                <input value={filters.city} onChange={(e) => setFilters((s) => ({ ...s, city: e.target.value }))} />
              </div>
            </div>
            <div className="col">
              <div className="field">
                <label>Order ID</label>
                <input
                  value={filters.order_id}
                  onChange={(e) => setFilters((s) => ({ ...s, order_id: e.target.value }))}
                />
              </div>
            </div>
          </div>
          <button className="btn btn-primary" disabled={busy}>
            {busy ? "Loading..." : "Apply Filters"}
          </button>
        </form>

        <div style={{ height: 14 }} />

        {rows.length ? (
          <>
            <table>
              <thead>
                <tr>
                  <th>User</th>
                  <th>Order ID</th>
                  <th>Type</th>
                  <th>Dealer</th>
                  <th>City</th>
                  <th>When</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((o) => (
                  <tr key={o.id}>
                    <td>{o.username}</td>
                    <td>{o.order_id}</td>
                    <td>{o.order_type || "-"}</td>
                    <td>{o.dealer_name}</td>
                    <td>{o.city}</td>
                    <td>{o.generated_at}</td>
                    <td style={{ whiteSpace: "nowrap" }}>
                      <button className="btn btn-primary" onClick={() => onDownload(o.report_name)}>
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ height: 12 }} />
            <div className="row">
              <button className="btn" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1}>
                Prev
              </button>
              <button className="btn" onClick={() => setPage((p) => p + 1)} disabled={rows.length < 25}>
                Next
              </button>
              <span className="muted" style={{ alignSelf: "center" }}>
                Page {page}
              </span>
            </div>
          </>
        ) : (
          <div className="muted">{busy ? "Loading..." : "No results."}</div>
        )}
      </div>
    </div>
  );
}

