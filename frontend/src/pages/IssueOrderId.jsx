import React from "react";
import * as api from "../api/client.js";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
  Grid,
  Stack,
  Chip,
} from "@mui/material";
import { Send } from "@mui/icons-material";

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
    <Stack spacing={3}>
      <Box>
        <Typography variant="h5" fontWeight="bold" gutterBottom>
          Issue Order ID
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Assign order IDs to team members/dealers
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {ok && <Alert severity="success">{ok}</Alert>}

      <Grid container spacing={3}>
        {/* Issue Form */}
        <Grid item xs={12} md={6}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Issue New ID
              </Typography>

              <Box component="form" onSubmit={onSubmit}>
                <Stack spacing={2}>
                  <TextField
                    fullWidth
                    label="Order ID"
                    value={orderId}
                    onChange={(e) => setOrderId(e.target.value.toUpperCase())}
                    required
                    inputProps={{ style: { textTransform: 'uppercase' } }}
                  />

                  <TextField
                    fullWidth
                    label="Given To"
                    value={givenTo}
                    onChange={(e) => setGivenTo(e.target.value)}
                    required
                    placeholder="Person/Team name"
                  />

                  <TextField
                    fullWidth
                    label="Dealer Name"
                    value={dealerName}
                    onChange={(e) => setDealerName(e.target.value)}
                    placeholder="Optional"
                  />

                  <TextField
                    fullWidth
                    label="City"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    placeholder="Optional"
                  />

                  <Button
                    type="submit"
                    variant="contained"
                    size="large"
                    disabled={busy}
                    startIcon={<Send />}
                    fullWidth
                  >
                    {busy ? "Issuing..." : "Issue ID"}
                  </Button>
                </Stack>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recently Issued */}
        <Grid item xs={12} md={6}>
          <Card elevation={2}>
            <CardContent>
              <Typography variant="h6" fontWeight="bold" gutterBottom>
                Recently Issued
              </Typography>

              {recent.length ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell><strong>Order ID</strong></TableCell>
                        <TableCell><strong>Given To</strong></TableCell>
                        <TableCell><strong>When</strong></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {recent.map((r) => (
                        <TableRow key={r.id} hover>
                          <TableCell>
                            <Chip label={r.order_id} size="small" color="secondary" />
                          </TableCell>
                          <TableCell>{r.given_to_name}</TableCell>
                          <TableCell>
                            <Typography variant="caption" color="text.secondary">
                              {r.given_at}
                            </Typography>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography color="text.secondary" textAlign="center" py={2}>
                  No issued IDs yet.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
