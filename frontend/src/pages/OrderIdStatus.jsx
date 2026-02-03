import React from "react";
import * as api from "../api/client.js";

export default function OrderIdStatus() {
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState("");

  async function load() {
    setError("");
    try {
      const res = await api.orderIdStatus();
      setData(res?.data || null);
    } catch (e) {
      setError(e?.message || "Failed to load");
    }
  }

  React.useEffect(() => {
    void load();
  }, []);

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Order ID Status</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Latest + suggested next Order ID.
        </p>
      </div>
      <div className="card-body">
        {error ? <div className="alert alert-error">{error}</div> : null}
        {!data ? (
          <div className="muted">Loading...</div>
        ) : (
          <>
            <div className="row">
              <div className="col card kpi">
                <div className="label">Latest</div>
                <div className="value" style={{ fontSize: 22 }}>
                  {data.latest_id || "None"}
                </div>
              </div>
              <div className="col card kpi">
                <div className="label">Suggested</div>
                <div className="value" style={{ fontSize: 22 }}>
                  {data.suggested_id}
                </div>
              </div>
            </div>

            <div style={{ height: 14 }} />

            <div className="card">
              <div className="card-header">
                <h3 style={{ margin: 0 }}>Recent Orders</h3>
              </div>
              <div className="card-body">
                {data.recent_orders?.length ? (
                  <table>
                    <thead>
                      <tr>
                        <th>Order ID</th>
                        <th>Dealer</th>
                        <th>City</th>
                        <th>Generated</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.recent_orders.map((o) => (
                        <tr key={`${o.order_id}-${o.generated_at}`}>
                          <td>{o.order_id}</td>
                          <td>{o.dealer_name}</td>
                          <td>{o.city}</td>
                          <td>{o.generated_at}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="muted">No recent orders.</div>
                )}
              </div>
            </div>
            <div style={{ height: 12 }} />
            <button className="btn" onClick={load}>
              Refresh
            </button>
          </>
        )}
      </div>
    </div>
  );
}

