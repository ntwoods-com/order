import React from "react";
import * as api from "../api/client.js";
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  CircularProgress,
  Alert,
  Stack,
  Divider,
} from "@mui/material";
import {
  TrendingUp,
  ShoppingCart,
  Today,
  CalendarMonth,
} from "@mui/icons-material";

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

  const kpiCards = data ? [
    {
      label: "Total Orders",
      value: data.overview.total_orders,
      icon: <TrendingUp sx={{ fontSize: 40 }} />,
      color: "primary",
    },
    {
      label: "My Orders",
      value: data.overview.user_orders,
      icon: <ShoppingCart sx={{ fontSize: 40 }} />,
      color: "secondary",
    },
    {
      label: "Today's Orders",
      value: data.overview.today_orders,
      icon: <Today sx={{ fontSize: 40 }} />,
      color: "success",
    },
    {
      label: "This Month",
      value: data.overview.month_orders,
      icon: <CalendarMonth sx={{ fontSize: 40 }} />,
      color: "info",
    },
  ] : [];

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" fontWeight="bold" gutterBottom>
          Dashboard
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Overview and quick statistics • {new Date().toLocaleDateString()}
        </Typography>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {!data ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <Stack spacing={2} alignItems="center">
            <CircularProgress />
            <Typography color="text.secondary">Loading dashboard data...</Typography>
          </Stack>
        </Box>
      ) : (
        <>
          {/* KPI Cards */}
          <Grid container spacing={3} sx={{ mb: 4 }}>
            {kpiCards.map((kpi, idx) => (
              <Grid item xs={12} sm={6} md={3} key={idx}>
                <Card
                  elevation={2}
                  sx={{
                    position: 'relative',
                    overflow: 'visible',
                    transition: 'all 0.3s',
                    '&:hover': {
                      transform: 'translateY(-8px)',
                      boxShadow: 6,
                    },
                  }}
                >
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
                      <Box>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {kpi.label}
                        </Typography>
                        <Typography variant="h4" fontWeight="bold" color={`${kpi.color}.main`}>
                          {kpi.value}
                        </Typography>
                      </Box>
                      <Box sx={{ color: `${kpi.color}.main`, opacity: 0.3 }}>
                        {kpi.icon}
                      </Box>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Tables */}
          <Grid container spacing={3}>
            {/* Recent Orders Table */}
            <Grid item xs={12} lg={7}>
              <Card elevation={2}>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" gutterBottom>
                    Recent Orders
                  </Typography>
                  <Divider sx={{ my: 2 }} />

                  {data.recent_orders?.length ? (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell><strong>Order ID</strong></TableCell>
                            <TableCell><strong>Dealer</strong></TableCell>
                            <TableCell><strong>City</strong></TableCell>
                            <TableCell><strong>User</strong></TableCell>
                            <TableCell><strong>Generated</strong></TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {data.recent_orders.map((o) => (
                            <TableRow
                              key={`${o.order_id}-${o.generated_at}`}
                              hover
                              sx={{ '&:last-child td': { border: 0 } }}
                            >
                              <TableCell>
                                <Chip
                                  label={o.order_id}
                                  size="small"
                                  color="primary"
                                  variant="outlined"
                                />
                              </TableCell>
                              <TableCell>{o.dealer_name}</TableCell>
                              <TableCell>{o.city}</TableCell>
                              <TableCell>{o.username}</TableCell>
                              <TableCell>
                                <Typography variant="caption" color="text.secondary">
                                  {new Date(o.generated_at).toLocaleString()}
                                </Typography>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  ) : (
                    <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                      No recent orders found.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>

            {/* Top Dealers Table */}
            <Grid item xs={12} lg={5}>
              <Card elevation={2}>
                <CardContent>
                  <Typography variant="h6" fontWeight="bold" gutterBottom>
                    Top Dealers
                  </Typography>
                  <Divider sx={{ my: 2 }} />

                  {data.top_dealers?.length ? (
                    <TableContainer>
                      <Table size="small">
                        <TableHead>
                          <TableRow>
                            <TableCell><strong>Dealer</strong></TableCell>
                            <TableCell><strong>City</strong></TableCell>
                            <TableCell align="right"><strong>Orders</strong></TableCell>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {data.top_dealers.map((d) => (
                            <TableRow
                              key={`${d.dealer_name}-${d.city}`}
                              hover
                              sx={{ '&:last-child td': { border: 0 } }}
                            >
                              <TableCell>
                                <Typography fontWeight="500" color="primary.main">
                                  {d.dealer_name}
                                </Typography>
                              </TableCell>
                              <TableCell>{d.city}</TableCell>
                              <TableCell align="right">
                                <Chip
                                  label={d.order_count}
                                  size="small"
                                  color="success"
                                />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </TableContainer>
                  ) : (
                    <Typography color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
                      No dealer data available.
                    </Typography>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </>
      )}
    </Box>
  );
}
