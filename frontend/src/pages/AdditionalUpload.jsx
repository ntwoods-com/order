import React from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client.js";
import {
  Box,
  Card,
  CardContent,
  Button,
  Typography,
  Alert,
  Stack,
} from "@mui/material";
import { CloudUpload, CheckCircle } from "@mui/icons-material";

const UPLOAD_KEY = "sale_order_upload_additional";

export function getAdditionalUploadState() {
  try {
    return JSON.parse(sessionStorage.getItem(UPLOAD_KEY) || "null");
  } catch {
    return null;
  }
}

export function setAdditionalUploadState(state) {
  sessionStorage.setItem(UPLOAD_KEY, JSON.stringify(state));
}

export default function AdditionalUpload() {
  const navigate = useNavigate();
  const [file, setFile] = React.useState(null);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  async function onUpload() {
    if (!file) return;
    setError("");
    setBusy(true);
    try {
      const res = await api.uploadExcel(file);
      setAdditionalUploadState(res?.data || null);
      navigate("/additional/details");
    } catch (e) {
      setError(e?.message || "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card elevation={2}>
      <CardContent>
        <Stack spacing={3}>
          <Box>
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              Additional Order - Upload Excel
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Generates a report using an existing Order ID
            </Typography>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}

          <Box>
            <Button
              component="label"
              variant="outlined"
              startIcon={<CloudUpload />}
              size="large"
              fullWidth
              sx={{ py: 2 }}
            >
              Choose Excel File
              <input
                type="file"
                hidden
                accept=".xls,.xlsx"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </Button>

            {file && (
              <Alert
                severity="success"
                icon={<CheckCircle />}
                sx={{ mt: 2 }}
              >
                <strong>{file.name}</strong> ({Math.round(file.size / 1024)} KB)
              </Alert>
            )}
          </Box>

          <Button
            variant="contained"
            size="large"
            onClick={onUpload}
            disabled={!file || busy}
            fullWidth
          >
            {busy ? "Uploading..." : "Upload & Continue"}
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
