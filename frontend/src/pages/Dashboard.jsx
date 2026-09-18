import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api.js";

function formatInr(amount) {
  return amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatWhen(iso) {
  if (!iso) return "";
  const date = new Date(iso);
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export default function Dashboard({ signOut }) {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [findings, setFindings] = useState([]);
  const [scanLatest, setScanLatest] = useState(null);

  const [scanStatus, setScanStatus] = useState("idle"); // idle | loading | started | error
  const [scanMessage, setScanMessage] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError("");
    try {
      const [findingsRes, scanRes] = await Promise.all([api.getFindings(), api.getScanLatest()]);
      setFindings(findingsRes.findings || []);
      setScanLatest(scanRes.scan || null);
    } catch (err) {
      setLoadError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleScanNow() {
    setScanStatus("loading");
    setScanMessage("");
    try {
      await api.startScan();
      setScanStatus("started");
      setScanMessage("Scan started. It usually takes a minute or two — refresh to see new results.");
    } catch (err) {
      setScanStatus("error");
      setScanMessage(err.message);
    }
  }

  const active = findings.filter((f) => f.status === "active");
  const resolved = findings.filter((f) => f.status !== "active");
  const total = active.reduce((sum, f) => sum + f.estDailyCostInr, 0);

  return (
    <div className="page">
      <header className="container">
        <div className="topbar">
          <Link to="/" className="wordmark" style={{ textDecoration: "none" }}>
            BillGuard<span className="dot">.</span>
          </Link>
          <button className="btn btn-quiet" onClick={signOut}>
            Sign out
          </button>
        </div>
      </header>

      <main className="container" style={{ paddingTop: 8, paddingBottom: 96 }}>
        <div
          className="stack gap-sm"
          style={{
            marginBottom: 32,
            display: "flex",
            flexDirection: "row",
            justifyContent: "space-between",
            alignItems: "flex-end",
            flexWrap: "wrap",
            gap: 20,
          }}
        >
          <div className="stack gap-xs">
            <span className="pill pill-teal">Read-only · connected</span>
            {scanLatest && (
              <p className="text-small text-faint" style={{ marginTop: 8 }}>
                Last scan {formatWhen(scanLatest.timestamp)} · {scanLatest.regionsScanned.length}{" "}
                region(s) checked
                {scanLatest.regionsSkipped.length > 0 &&
                  ` · ${scanLatest.regionsSkipped.length} skipped`}
              </p>
            )}
          </div>
          <div className="stack gap-xs" style={{ alignItems: "flex-end" }}>
            <button
              className="btn btn-outline"
              onClick={handleScanNow}
              disabled={scanStatus === "loading"}
            >
              {scanStatus === "loading" ? "Starting…" : "Scan now"}
            </button>
          </div>
        </div>

        {scanMessage && (
          <div
            className={scanStatus === "error" ? "error-banner" : "pill pill-amber"}
            style={{ marginBottom: 28, display: "block", padding: scanStatus === "error" ? undefined : "12px 14px" }}
          >
            {scanMessage}
          </div>
        )}

        {loading && (
          <div className="stack gap-sm" style={{ padding: "40px 0" }}>
            <p className="text-muted">Scanning every region…</p>
            <div className="scan-sweep" style={{ maxWidth: 320 }} />
          </div>
        )}

        {!loading && loadError && <div className="error-banner">{loadError}</div>}

        {!loading && !loadError && (
          <>
            <div
              className="panel"
              style={{
                marginBottom: 36,
                display: "flex",
                alignItems: "baseline",
                justifyContent: "space-between",
                flexWrap: "wrap",
                gap: 12,
              }}
            >
              <div>
                <div style={{ fontSize: "2.2rem", color: "var(--amber)", fontWeight: 600 }}>
                  ₹{formatInr(total)}
                  <span className="text-small text-faint" style={{ marginLeft: 6 }}>
                    / day
                  </span>
                </div>
                <p className="text-small text-muted" style={{ marginTop: 4 }}>
                  still on the clock across {active.length}{" "}
                  {active.length === 1 ? "thing" : "things"}
                </p>
              </div>
            </div>

            {active.length === 0 ? (
              <div className="empty-state">
                <span className="mark">✓</span>
                <h3 className="text-h3">Nothing's running that shouldn't be.</h3>
                <p className="text-muted">
                  BillGuard checks again tomorrow, or scan now if you just changed something.
                </p>
              </div>
            ) : (
              <div className="findings-list">
                {active.map((f) => (
                  <FindingRow key={`${f.region}-${f.resourceId}`} finding={f} />
                ))}
              </div>
            )}

            {resolved.length > 0 && (
              <div className="stack gap-sm" style={{ marginTop: 40 }}>
                <h3 className="text-h3 text-muted">Resolved recently</h3>
                <div className="findings-list">
                  {resolved.map((f) => (
                    <FindingRow key={`${f.region}-${f.resourceId}`} finding={f} resolved />
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function FindingRow({ finding, resolved }) {
  return (
    <div className={`finding-row${resolved ? " resolved" : ""}`}>
      <div className="type">{finding.type}</div>
      <div className="cost">
        ₹{formatInr(finding.estDailyCostInr)}
        <span className="unit">/day</span>
      </div>
      <div className="meta">
        <span>{finding.region}</span>
        <span>{finding.name}</span>
        {resolved ? <span>resolved</span> : <span>since {formatWhen(finding.firstSeen)}</span>}
      </div>
      {!resolved && <div className="howto">{finding.howToDelete}</div>}
    </div>
  );
}
