import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { api } from "../api.js";

/**
 * Routes a signed-in user by whether they've already connected an AWS
 * account, so that connecting is a one-time step:
 *   requires="connected"     -> unconnected users are sent to /connect
 *   requires="not-connected" -> connected users are sent to /dashboard
 */
export default function ConnectionGate({ requires, children }) {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    api
      .getConnectStatus()
      .then((data) => !cancelled && setState({ status: "ready", connection: data.status }))
      .catch((err) => !cancelled && setState({ status: "error", message: err.message }));
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <div className="page">
        <div className="container stack gap-sm" style={{ paddingTop: 96 }}>
          <p className="text-muted">Checking your account…</p>
          <div className="scan-sweep" style={{ maxWidth: 320 }} />
        </div>
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="page">
        <div className="container" style={{ paddingTop: 96, maxWidth: 640 }}>
          <div className="error-banner">
            Couldn't check your connection status: {state.message}. Refresh to try again.
          </div>
        </div>
      </div>
    );
  }

  const connected = state.connection === "connected";
  if (requires === "connected" && !connected) return <Navigate to="/connect" replace />;
  if (requires === "not-connected" && connected) return <Navigate to="/dashboard" replace />;

  return children;
}
