import React from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client.js";
import { triggerDownload } from "../components/download.js";
import { getAdditionalUploadState, setAdditionalUploadState } from "./AdditionalUpload.jsx";
import {
  Box,
  Card,
  CardContent,
  Typography,
  TextField,
  Button,
  Alert,
  Grid,
  Stack,
  Chip,
} from "@mui/material";
import { Download, NavigateNext, Add } from "@mui/icons-material";

export default function AdditionalDetails() {
  const navigate = useNavigate();
  const upload = getAdditionalUploadState();

  const [existingOrderId, setExistingOrderId] = React.useState("");
  const [dealerName, setDealerName] = React.useState("");
  const [city, setCity] = React.useState("");
  const [orderDate, setOrderDate] = React.useState(() => new Date().toISOString().slice(0, 10));
  const [freight, setFreight] = React.useState("");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [result, setResult] = React.useState(null);

  React.useEffect(() => {
    if (!upload?.upload_id) navigate("/additional/upload", { replace: true });
  }, [upload, navigate]);

  async function onGenerate(e) {
    e.preventDefault();
    if (!upload?.upload_id) return;
    setError("");
    setBusy(true);
    try {
      const res = await api.generateReport({
        upload_id: upload.upload_id,
        dealer_name: dealerName,
        city,
        order_date: orderDate,
        freight_condition: freight,
        custom_order_id: existingOrderId,
        is_additional_order: true,
      });
      setResult(res?.data || null);
      setAdditionalUploadState(null);
    } catch (e2) {
      setError(e2?.message || "Failed to generate report");
    } finally {
      setBusy(false);
    }
  }

  async function onDownload() {
    if (!result?.report_name) return;
    const blob = await api.downloadReportBlob(result.report_name);
    triggerDownload(blob, result.report_name);
  }

  return (
    <Card elevation={2}>
      <CardContent>
        <Stack spacing={3}>
          <Box>
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              Additional Order - Details
            </Typography>
            <Typography variant="body2" color="text.secondary">
              File: <Chip label={upload?.filename} size="small" />
            </Typography>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}

          {result ? (
            <Alert severity="success">
              <Typography fontWeight="bold" gutterBottom>
                Additional Report Generated Successfully!
              </Typography>
              <Typography variant="body2" gutterBottom>
                Order ID: <Chip label={result.order_id} color="primary" size="small" />
              </Typography>
              <Typography variant="body2" gutterBottom>
                Report: <Chip label={result.report_name} size="small" />
              </Typography>

              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                <Button
                  variant="contained"
                  startIcon={<Download />}
                  onClick={onDownload}
                >
                  Download
                </Button>
                <Button
                  variant="outlined"
                  onClick={() => navigate("/orders")}
                >
                  Go to My Orders
                </Button>
                <Button
                  variant="outlined"
                  startIcon={<Add />}
                  onClick={() => navigate("/additional/upload")}
                >
                  Create Another
                </Button>
              </Stack>
            </Alert>
          ) : (
            <Box component="form" onSubmit={onGenerate}>
              <Stack spacing={2.5}>
                <Alert severity="info">
                  <Typography variant="body2">
                    This report will reuse an existing Order ID
                  </Typography>
                </Alert>

                <TextField
                  fullWidth
                  label="Existing Order ID"
                  value={existingOrderId}
                  onChange={(e) => setExistingOrderId(e.target.value.toUpperCase())}
                  placeholder="e.g. NTWS/2025/0523/01"
                  required
                  inputProps={{ style: { textTransform: 'uppercase' } }}
                />

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Dealer Name"
                      value={dealerName}
                      onChange={(e) => setDealerName(e.target.value)}
                      required
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="City"
                      value={city}
                      onChange={(e) => setCity(e.target.value)}
                      required
                    />
                  </Grid>
                </Grid>

                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Order Date"
                      type="date"
                      value={orderDate}
                      onChange={(e) => setOrderDate(e.target.value)}
                      required
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <TextField
                      fullWidth
                      label="Freight Condition"
                      value={freight}
                      onChange={(e) => setFreight(e.target.value)}
                      placeholder="e.g. FOB"
                    />
                  </Grid>
                </Grid>

                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={busy}
                  endIcon={<NavigateNext />}
                >
                  {busy ? "Generating..." : "Generate Additional Report"}
                </Button>
              </Stack>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
