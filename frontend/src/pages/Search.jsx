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
  Stack,
  Chip,
  InputAdornment,
} from "@mui/material";
import { Search as SearchIcon } from "@mui/icons-material";

export default function Search() {
  const [q, setQ] = React.useState("");
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState("");
  const [results, setResults] = React.useState([]);

  async function onSearch(e) {
    e.preventDefault();
    const query = q.trim();
    if (query.length < 2) {
      setError("Type at least 2 characters");
      return;
    }
    setError("");
    setBusy(true);
    try {
      const res = await api.searchOrders(query);
      setResults(res?.results || []);
    } catch (e2) {
      setError(e2?.message || "Search failed");
      setResults([]);
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
              Search Orders
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Search by dealer, city, order ID, or username
            </Typography>
          </Box>

          {error && <Alert severity="error">{error}</Alert>}

          <Box component="form" onSubmit={onSearch}>
            <Stack direction="row" spacing={2}>
              <TextField
                fullWidth
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="e.g. Mumbai / dealer / 02-26-00010"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon />
                    </InputAdornment>
                  ),
                }}
              />
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={busy}
                sx={{ minWidth: 120 }}
              >
                {busy ? "Searching..." : "Search"}
              </Button>
            </Stack>
          </Box>

          {results.length > 0 && (
            <TableContainer>
              <Table>
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
                  {results.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell>
                        <Chip label={r.order_id} color="primary" size="small" variant="outlined" />
                      </TableCell>
                      <TableCell>{r.dealer_name}</TableCell>
                      <TableCell>{r.city}</TableCell>
                      <TableCell>{r.username}</TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {r.generated_at}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}

          {!busy && results.length === 0 && q && (
            <Typography color="text.secondary" textAlign="center" py={2}>
              No results found
            </Typography>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
