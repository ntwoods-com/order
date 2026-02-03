import React from "react";
import { Link } from "react-router-dom";

export default function NotFound() {
  return (
    <div className="card">
      <div className="card-body">
        <h2 style={{ marginTop: 0 }}>Not found</h2>
        <p className="muted">This route does not exist.</p>
        <Link className="btn btn-primary" to="/dashboard">
          Go to Dashboard
        </Link>
      </div>
    </div>
  );
}

