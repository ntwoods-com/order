import React from "react";
import * as api from "../api/client.js";
import { triggerDownload } from "../components/download.js";
import {
  Box,
  Card,
  CardContent,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Alert,
  CircularProgress,
  Stack,
  Chip,
  Pagination,
} from "@mui/material";
import { Download } from "@mui/icons-material";

export default function Orders() {
  const [rows, setRows] = React.useState([]);
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [page, setPage] = React.useState(1);
  const [perPage] = React.useState(20);

  async function load(p) {
    setError("");
    setBusy(true);
    try {
      const res = await api.ordersList({ page: String(p), per_page: String(perPage) });
      setRows(res?.data?.orders || []);
    } catch (e) {
      setError(e?.message || "Failed to load orders");
    } finally {
      setBusy(false);
    }
  }

  React.useEffect(() => {
    void load(page);
  }, [page]);

  async function onDownload(reportName) {
    try {
      const blob = await api.downloadReportBlob(reportName);
      triggerDownload(blob, reportName);
    } catch (e) {
      setError(e?.message || "Download failed");
    }
  }

  return (
    <Card elevation={2}>
      <CardContent>
        <Stack spacing={3}>
          <Box>
            <Typography variant="h5" fontWeight="bold" gutterBottom>
              My Orders
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Latest generated orders (download from here anytime)
            </Typography>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}

          {busy ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress />
            </Box>
          ) : rows.length ? (
            <>
              <TableContainer>
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell><strong>Order ID</strong></TableCell>
                      <TableCell><strong>Dealer</strong></TableCell>
                      <TableCell><strong>City</strong></TableCell>
                      <TableCell><strong>Generated</strong></TableCell>
                      <TableCell><strong>Report</strong></TableCell>
                      <TableCell align="right"><strong>Action</strong></TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((o) => (
                      <TableRow key={o.id} hover>
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
                        <TableCell>
                          <Typography variant="caption">{o.report_name}</Typography>
                        </TableCell>
                        <TableCell align="right">
                          <Button
                            variant="contained"
                            size="small"
                            startIcon={<Download />}
                            onClick={() => onDownload(o.report_name)}
                          >
                            Download
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>

              <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
                <Pagination
                  count={rows.length < perPage ? page : page + 1}
                  page={page}
                  onChange={(e, value) => setPage(value)}
                  color="primary"
                />
              </Box>
            </>
          ) : (
            <Typography color="text.secondary" textAlign="center" py={4}>
              No orders yet.
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
