import React from "react";
import * as api from "../api/client.js";
import { triggerDownload } from "../components/download.js";

export default function Orders() {
  const [rows, setRows] = React.useState([]);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [perPage] = React.useState(20);

  async function load(p) {
    setError("");
    setBusy(true);
    try {
      const res = await api.ordersList({ page: String(p), per_page: String(perPage) });
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
        <h2 style={{ margin: 0 }}>My Orders</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Latest generated orders (download from here anytime)
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        {busy ? (
          <div className="muted">Loading...</div>
        ) : rows.length ? (
          <>
            <table>
              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Dealer</th>
                  <th>City</th>
                  <th>Generated</th>
                  <th>Report</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {rows.map((o) => (
                  <tr key={o.id}>
                    <td>{o.order_id}</td>
                    <td>{o.dealer_name}</td>
                    <td>{o.city}</td>
                    <td>{o.generated_at}</td>
                    <td style={{ fontSize: 12 }}>{o.report_name}</td>
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
              <button className="btn" onClick={() => setPage((p) => p + 1)} disabled={rows.length < perPage}>
                Next
              </button>
              <span className="muted" style={{ alignSelf: "center" }}>
                Page {page}
              </span>
            </div>
          </>
        ) : (
          <div className="muted">No orders yet.</div>
        )}
      </div>
    </div>
  );
}

