import React from "react";
import * as api from "../api/client.js";

export default function IssueOrderId() {
  const [suggested, setSuggested] = React.useState("");
  const [orderId, setOrderId] = React.useState("");
  const [givenTo, setGivenTo] = React.useState("");
  const [dealerName, setDealerName] = React.useState("");
  const [city, setCity] = React.useState("");
  const [error, setError] = React.useState("");
  const [ok, setOk] = React.useState("");
  const [recent, setRecent] = React.useState([]);
  const [busy, setBusy] = React.useState(false);

  async function load() {
    try {
      const status = await api.orderIdStatus();
      const s = status?.data?.suggested_id || "";
      setSuggested(s);
      setOrderId((cur) => (cur ? cur : s));
      const issued = await api.issuedIds({ page: "1", per_page: "10" });
      setRecent(issued?.data?.issued_ids || []);
    } catch (e) {
      setError(e?.message || "Failed to load");
    }
  }

  React.useEffect(() => {
    void load();
  }, []);

  async function onSubmit(e) {
    e.preventDefault();
    setError("");
    setOk("");
    setBusy(true);
    try {
      await api.issueOrderId({
        order_id: orderId.trim(),
        given_to_name: givenTo.trim(),
        dealer_name: dealerName.trim(),
        city: city.trim(),
      });
      setOk(`Issued ${orderId.trim()} to ${givenTo.trim()}`);
      setGivenTo("");
      setDealerName("");
      setCity("");
      setOrderId(suggested);
      await load();
    } catch (e2) {
      setError(e2?.message || "Failed to issue");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Issue Order ID</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Assign order IDs to team members/dealers.
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        {ok ? <div className="alert alert-success">{ok}</div> : null}

        <div className="split">
          <div className="card">
            <div className="card-header">
              <h3 style={{ margin: 0 }}>Issue New</h3>
            </div>
            <div className="card-body">
              <form onSubmit={onSubmit}>
                <div className="field">
                  <label>Order ID *</label>
                  <input value={orderId} onChange={(e) => setOrderId(e.target.value.toUpperCase())} required />
                </div>
                <div className="field">
                  <label>Given To *</label>
                  <input value={givenTo} onChange={(e) => setGivenTo(e.target.value)} required />
                </div>
                <div className="field">
                  <label>Dealer Name</label>
                  <input value={dealerName} onChange={(e) => setDealerName(e.target.value)} />
                </div>
                <div className="field">
                  <label>City</label>
                  <input value={city} onChange={(e) => setCity(e.target.value)} />
                </div>
                <button className="btn btn-primary" disabled={busy}>
                  {busy ? "Issuing..." : "Issue"}
                </button>
              </form>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h3 style={{ margin: 0 }}>Recently Issued</h3>
            </div>
            <div className="card-body">
              {recent.length ? (
                <table>
                  <thead>
                    <tr>
                      <th>Order ID</th>
                      <th>Given To</th>
                      <th>Dealer</th>
                      <th>When</th>
                      <th>By</th>
                    </tr>
                  </thead>
                  <tbody>
                    {recent.map((r) => (
                      <tr key={r.id}>
                        <td>{r.order_id}</td>
                        <td>{r.given_to_name}</td>
                        <td>{r.dealer_name || "-"}</td>
                        <td>{r.given_at}</td>
                        <td>{r.given_by_user}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <div className="muted">No issued IDs yet.</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

