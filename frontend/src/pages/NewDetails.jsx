import React from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client.js";
import { triggerDownload } from "../components/download.js";
import { getNewUploadState, setNewUploadState } from "./NewUpload.jsx";
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
  CircularProgress,
} from "@mui/material";
import { Download, NavigateNext, Add } from "@mui/icons-material";

export default function NewDetails() {
  const navigate = useNavigate();
  const upload = getNewUploadState();

  const [dealerName, setDealerName] = React.useState("");
  const [city, setCity] = React.useState("");
  const [orderDate, setOrderDate] = React.useState(() => new Date().toISOString().slice(0, 10));
  const [freight, setFreight] = React.useState("");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [downloadBusy, setDownloadBusy] = React.useState(false);
  const [result, setResult] = React.useState(null);
  const autoDownloadedRef = React.useRef(false);

  React.useEffect(() => {
    if (!upload?.upload_id) navigate("/new/upload", { replace: true });
  }, [upload, navigate]);

  async function downloadReport(reportName) {
    if (!reportName) return;
    setError("");
    setDownloadBusy(true);
    try {
      const blob = await api.downloadReportBlob(reportName);
      triggerDownload(blob, reportName);
    } catch (e2) {
      setError(e2?.message || "Download failed");
    } finally {
      setDownloadBusy(false);
    }
  }

  React.useEffect(() => {
    if (!result?.report_name) return;
    if (autoDownloadedRef.current) return;
    autoDownloadedRef.current = true;
    void downloadReport(result.report_name);
  }, [result?.report_name]);

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
        is_additional_order: false,
      });
      setResult(res?.data || null);
      setNewUploadState(null);
    } catch (e2) {
      setError(e2?.message || "Failed to generate report");
    } finally {
      setBusy(false);
    }
  }

  async function onDownload() {
    if (!result?.report_name) return;
    void downloadReport(result.report_name);
  }

  return (
    <Card elevation={2}>
      <CardContent>
        <Stack spacing={3}>
          <Box>
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              New Order - Details
            </Typography>
            <Typography variant="body2" color="text.secondary">
              File: <Chip label={upload?.filename} size="small" />
            </Typography>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}

          {result ? (
            <Alert severity="success">
              <Typography fontWeight="bold" gutterBottom>
                Report Generated Successfully!
              </Typography>
              <Typography variant="body2" gutterBottom>
                Order ID: <Chip label={result.order_id} color="primary" size="small" />
              </Typography>
              <Typography variant="body2" gutterBottom>
                Report: <Chip label={result.report_name} size="small" />
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Download will start automatically. If it doesn&apos;t, click Download.
              </Typography>

              <Stack direction="row" spacing={2} sx={{ mt: 2 }}>
                <Button
                  variant="contained"
                  startIcon={downloadBusy ? <CircularProgress size={18} color="inherit" /> : <Download />}
                  onClick={onDownload}
                  disabled={downloadBusy}
                >
                  {downloadBusy ? "Downloading..." : "Download"}
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
                  onClick={() => navigate("/new/upload")}
                >
                  Create Another
                </Button>
              </Stack>
            </Alert>
          ) : (
            <Box component="form" onSubmit={onGenerate}>
              <Stack spacing={2.5}>
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
                  {busy ? "Generating..." : "Generate Report"}
                </Button>
              </Stack>
            </Box>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
