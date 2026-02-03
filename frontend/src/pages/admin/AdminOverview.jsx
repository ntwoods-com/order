import React from "react";
import * as api from "../../api/client.js";

export default function AdminOverview() {
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState("");

  async function load() {
    setError("");
    try {
      const res = await api.adminOverview();
      setData(res?.data || null);
    } catch (e) {
      setError(e?.message || "Failed to load admin overview");
    }
  }

  React.useEffect(() => {
    void load();
  }, []);

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Admin</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Overview + active sessions
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
                <div className="label">Total Orders</div>
                <div className="value">{data.stats.total_orders}</div>
              </div>
              <div className="col card kpi">
                <div className="label">Today</div>
                <div className="value">{data.stats.today_orders}</div>
              </div>
              <div className="col card kpi">
                <div className="label">Issued IDs</div>
                <div className="value">{data.stats.issued_ids}</div>
              </div>
              <div className="col card kpi">
                <div className="label">Active Sessions</div>
                <div className="value">{data.stats.active_sessions}</div>
              </div>
            </div>

            <div style={{ height: 14 }} />

            <div className="split">
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
                          <th>User</th>
                          <th>When</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.recent_orders.map((o) => (
                          <tr key={`${o.order_id}-${o.generated_at}`}>
                            <td>{o.order_id}</td>
                            <td>{o.dealer_name}</td>
                            <td>{o.city}</td>
                            <td>{o.username}</td>
                            <td>{o.generated_at}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="muted">No orders.</div>
                  )}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h3 style={{ margin: 0 }}>Active Sessions</h3>
                </div>
                <div className="card-body">
                  {data.sessions?.length ? (
                    <table>
                      <thead>
                        <tr>
                          <th>User</th>
                          <th>IP</th>
                          <th>Issued</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.sessions.map((s) => (
                          <tr key={s.username}>
                            <td>{s.username}</td>
                            <td>{s.ip || "-"}</td>
                            <td>{s.issued_at || "-"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="muted">No active sessions.</div>
                  )}
                </div>
              </div>
            </div>
            <div style={{ height: 12 }} />
            <div className="row">
              <a className="btn" href="#/admin/users">
                Users
              </a>
              <a className="btn" href="#/admin/orders">
                Orders
              </a>
              <a className="btn" href="#/admin/sessions">
                Sessions
              </a>
              <a className="btn" href="#/admin/logs">
                Logs
              </a>
              <button className="btn" onClick={load}>
                Refresh
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

