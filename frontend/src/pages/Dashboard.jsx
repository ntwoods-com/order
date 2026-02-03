import React from "react";
import * as api from "../api/client.js";

export default function Dashboard() {
  const [data, setData] = React.useState(null);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let cancelled = false;
    (async () => {
      setError("");
      try {
        const res = await api.dashboardStats();
        if (!cancelled) setData(res?.data || null);
      } catch (e) {
        if (!cancelled) setError(e?.message || "Failed to load dashboard");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="card">
      <div className="card-header">
        <h2 style={{ margin: 0 }}>Dashboard</h2>
        <p className="muted" style={{ marginTop: 6 }}>
          Overview + quick stats
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
                <div className="value">{data.overview.total_orders}</div>
              </div>
              <div className="col card kpi">
                <div className="label">My Orders</div>
                <div className="value">{data.overview.user_orders}</div>
              </div>
              <div className="col card kpi">
                <div className="label">Today</div>
                <div className="value">{data.overview.today_orders}</div>
              </div>
              <div className="col card kpi">
                <div className="label">This Month</div>
                <div className="value">{data.overview.month_orders}</div>
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
                          <th>Generated</th>
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
                    <div className="muted">No recent orders.</div>
                  )}
                </div>
              </div>

              <div className="card">
                <div className="card-header">
                  <h3 style={{ margin: 0 }}>Top Dealers</h3>
                </div>
                <div className="card-body">
                  {data.top_dealers?.length ? (
                    <table>
                      <thead>
                        <tr>
                          <th>Dealer</th>
                          <th>City</th>
                          <th>Orders</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.top_dealers.map((d) => (
                          <tr key={`${d.dealer_name}-${d.city}`}>
                            <td>{d.dealer_name}</td>
                            <td>{d.city}</td>
                            <td>{d.order_count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <div className="muted">No data.</div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

