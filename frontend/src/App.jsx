import React from "react";
import { HashRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthContext.jsx";
import { ThemeProvider } from "./auth/ThemeContext.jsx";
import RequireAuth from "./components/RequireAuth.jsx";
import RequireAdmin from "./components/RequireAdmin.jsx";
import Layout from "./components/Layout.jsx";

import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import NewUpload from "./pages/NewUpload.jsx";
import NewDetails from "./pages/NewDetails.jsx";
import AdditionalUpload from "./pages/AdditionalUpload.jsx";
import AdditionalDetails from "./pages/AdditionalDetails.jsx";
import Orders from "./pages/Orders.jsx";
import Search from "./pages/Search.jsx";
import OrderIdStatus from "./pages/OrderIdStatus.jsx";
import IssueOrderId from "./pages/IssueOrderId.jsx";
import AdminOverview from "./pages/admin/AdminOverview.jsx";
import AdminUsers from "./pages/admin/AdminUsers.jsx";
import AdminOrders from "./pages/admin/AdminOrders.jsx";
import AdminSessions from "./pages/admin/AdminSessions.jsx";
import AdminLogs from "./pages/admin/AdminLogs.jsx";
import NotFound from "./pages/NotFound.jsx";

export default function App() {
  return (
    <ThemeProvider>
      <HashRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route element={<RequireAuth />}>
              <Route element={<Layout />}>
                <Route index element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />

                <Route path="/new/upload" element={<NewUpload />} />
                <Route path="/new/details" element={<NewDetails />} />

                <Route path="/additional/upload" element={<AdditionalUpload />} />
                <Route path="/additional/details" element={<AdditionalDetails />} />

                <Route path="/orders" element={<Orders />} />
                <Route path="/search" element={<Search />} />
                <Route path="/order-id" element={<OrderIdStatus />} />
                <Route path="/issue-order-id" element={<IssueOrderId />} />

                <Route element={<RequireAdmin />}>
                  <Route path="/admin" element={<AdminOverview />} />
                  <Route path="/admin/users" element={<AdminUsers />} />
                  <Route path="/admin/orders" element={<AdminOrders />} />
                  <Route path="/admin/sessions" element={<AdminSessions />} />
                  <Route path="/admin/logs" element={<AdminLogs />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<NotFound />} />
          </Routes>
        </AuthProvider>
      </HashRouter>
    </ThemeProvider>
  );
}
