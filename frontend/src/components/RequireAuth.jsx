import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext.jsx";

export default function RequireAuth() {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="container">
        <div className="card">
          <div className="card-body">Loading...</div>
        </div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}

