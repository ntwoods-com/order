import { clearToken, getToken } from "./storage.js";

const RAW_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";
export const API_BASE_URL = String(RAW_BASE).replace(/\/$/, "");

function withAuthHeaders(headers = {}) {
  const token = getToken();
  if (!token) return headers;
  return { ...headers, Authorization: `Bearer ${token}` };
}

async function apiFetch(path, { method = "GET", body, headers = {}, auth = true } = {}) {
  const url = `${API_BASE_URL}${path}`;
  const finalHeaders = auth ? withAuthHeaders(headers) : headers;

  const res = await fetch(url, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...finalHeaders,
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearToken();
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.error || data?.message || `Request failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

export async function login(username, password) {
  return apiFetch("/api/v1/auth/login", { method: "POST", auth: false, body: { username, password } });
}

export async function me() {
  return apiFetch("/api/v1/auth/me");
}

export async function logout() {
  return apiFetch("/api/v1/auth/logout", { method: "POST", body: {} });
}

export async function dashboardStats() {
  return apiFetch("/api/v1/dashboard/stats");
}

export async function ordersList(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return apiFetch(`/api/v1/orders${qs ? `?${qs}` : ""}`);
}

export async function searchOrders(q) {
  const qs = new URLSearchParams({ q }).toString();
  return apiFetch(`/api/v1/orders/search?${qs}`);
}

export async function orderIdStatus() {
  return apiFetch("/api/v1/order-ids/status");
}

export async function issueOrderId(payload) {
  return apiFetch("/api/v1/issued-ids", { method: "POST", body: payload });
}

export async function issuedIds(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return apiFetch(`/api/v1/issued-ids${qs ? `?${qs}` : ""}`);
}

export async function uploadExcel(file) {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}/api/v1/uploads`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: (() => {
      const fd = new FormData();
      fd.append("file", file);
      return fd;
    })(),
  });

  if (res.status === 401) {
    clearToken();
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data?.error || `Upload failed (${res.status})`;
    throw new Error(msg);
  }
  return data;
}

export async function generateReport(payload) {
  return apiFetch("/api/v1/reports", { method: "POST", body: payload });
}

export async function downloadReportBlob(reportName) {
  const token = getToken();
  const res = await fetch(`${API_BASE_URL}/api/v1/reports/${encodeURIComponent(reportName)}`, {
    method: "GET",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });

  if (res.status === 401) {
    clearToken();
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    const msg = data?.error || `Download failed (${res.status})`;
    throw new Error(msg);
  }

  const blob = await res.blob();
  return blob;
}

// ---- Admin ----
export async function adminOverview() {
  return apiFetch("/api/v1/admin/overview");
}

export async function adminUsers() {
  return apiFetch("/api/v1/admin/users");
}

export async function adminOrders(params = {}) {
  const qs = new URLSearchParams(params).toString();
  return apiFetch(`/api/v1/admin/orders${qs ? `?${qs}` : ""}`);
}

export async function adminSessions() {
  return apiFetch("/api/v1/admin/sessions");
}

export async function adminRevokeSession(username) {
  return apiFetch(`/api/v1/admin/sessions/revoke/${encodeURIComponent(username)}`, { method: "POST", body: {} });
}

export async function adminRevokeAllSessions() {
  return apiFetch("/api/v1/admin/sessions/revoke-all", { method: "POST", body: {} });
}

export async function adminLogs(lines = 500) {
  const qs = new URLSearchParams({ lines: String(lines) }).toString();
  return apiFetch(`/api/v1/admin/logs?${qs}`);
}
