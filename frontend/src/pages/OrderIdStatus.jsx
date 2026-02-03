import React from "react";
import * as api from "../api/client.js";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Grid,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  CircularProgress,
  Stack,
  Chip,
  Paper,
} from "@mui/material";
import { Refresh, TrendingUp } from "@mui/icons-material";

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
    <Stack spacing={3}>
      <Box>
        <Typography variant="h5" fontWeight="bold" gutterBottom>
          Order ID Status
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Latest and suggested next Order ID
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      {!data ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
          <CircularProgress />
        </Box>
      ) : (
        <>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6}>
              <Card elevation={3} sx={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
                <CardContent>
                  <Typography variant="body2" color="white" gutterBottom>
                    Latest Order ID
                  </Typography>
                  <Typography variant="h4" fontWeight="bold" color="white">
                    {data.latest_id || "None"}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Card elevation={3} sx={{ background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)' }}>
                <CardContent>
                  <Stack direction="row" spacing={1} alignItems="center">
                    <TrendingUp sx={{ color: 'white' }} />
                    <Box>
                      <Typography variant="body2" color="white" gutterBottom>
                        Suggested Next ID
                      </Typography>
                      <Typography variant="h4" fontWeight="bold" color="white">
                        {data.suggested_id}
                      </Typography>
                    </Box>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Recent Orders
              </Typography>

              {data.recent_orders?.length ? (
                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Order ID</strong></TableCell>
                        <TableCell><strong>Dealer</strong></TableCell>
                        <TableCell><strong>City</strong></TableCell>
                        <TableCell><strong>Generated</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {data.recent_orders.map((o) => (
                        <TableRow key={`${o.order_id}-${o.generated_at}`} hover>
                          <TableCell>
                            <Chip label={o.order_id} color="primary" size="small" variant="outlined" />
                          </TableCell>
                          <TableCell>{o.dealer_name}</TableCell>
                          <TableCell>{o.city}</TableCell>
                          <TableCell>
                            <Typography variant="caption" color="text.secondary">
                              {o.generated_at}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="text.secondary" textAlign="center" py={2}>
                  No recent orders.
                </Typography>
              )}
            </CardContent>
          </Card>

          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={load}
            sx={{ alignSelf: 'flex-start' }}
          >
            Refresh
          </Button>
        </>
      )}
    </Stack>
  );
}
