import React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";
import { useTheme } from "../auth/ThemeContext.jsx";
import * as api from "../api/client.js";

function NavItem({ to, children, end }) {
  return (
    <NavLink to={to} end={end} className={({ isActive }) => (isActive ? "active" : "")}>
      {children}
    </NavLink>
  );
}

export default function Layout() {
  const { user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();

  return (
    <>
      <div className="topbar">
        <div className="topbar-inner">
          <div className="brand">
            <span className="brand-icon">📦</span>
            Sale Order System
          </div>
          <div className="nav">
            <NavItem to="/dashboard" end>
              Dashboard
            </NavItem>
            <NavItem to="/new/upload">New Order</NavItem>
            <NavItem to="/additional/upload">Additional</NavItem>
            <NavItem to="/orders">My Orders</NavItem>
            <NavItem to="/search">Search</NavItem>
            <NavItem to="/order-id">Order IDs</NavItem>
            <NavItem to="/issue-order-id">Issue ID</NavItem>
            {user?.is_admin ? <NavItem to="/admin">Admin</NavItem> : null}
          </div>
          <div className="nav-actions">
            <button className="theme-toggle" onClick={toggleTheme} title={isDark ? "Switch to Light" : "Switch to Dark"}>
              {isDark ? "☀️" : "🌙"}
            </button>
            <span className="user-name">
              {user?.username}
            </span>
            <button
              className="btn btn-danger"
              onClick={async () => {
                try {
                  await api.logout();
                } catch {
                  // ignore
                }
                logout();
                navigate("/login", { replace: true });
              }}
            >
              Logout
            </button>
          </div>
        </div>
      </div>
      <div className="container">
        <Outlet />
      </div>
    </>
  );
}
