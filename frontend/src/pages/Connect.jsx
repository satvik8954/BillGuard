import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";

import { api } from "../api.js";

export default function Connect({ signOut }) {
  const navigate = useNavigate();

  const [initStatus, setInitStatus] = useState("idle"); // idle | loading | done | error
  const [initError, setInitError] = useState("");
  const [quickCreateUrl, setQuickCreateUrl] = useState("");

  const [roleArn, setRoleArn] = useState("");
  const [verifyStatus, setVerifyStatus] = useState("idle"); // idle | loading | error
  const [verifyError, setVerifyError] = useState("");

  async function handleOpenCloudFormation() {
    const alreadyOpened = initStatus === "done";
    if (alreadyOpened) {
      const proceed = window.confirm(
        "You already opened CloudFormation once this session. If you already created the " +
          "stack, opening it again is unnecessary — reopen it below instead. Continue anyway?"
      );
      if (!proceed) return;
    }

    setInitStatus("loading");
    setInitError("");
    try {
      const data = await api.connectInit();
      setQuickCreateUrl(data.quickCreateUrl);
      setInitStatus("done");
      window.open(data.quickCreateUrl, "_blank", "noopener");
    } catch (err) {
      setInitStatus("error");
      setInitError(err.message);
    }
  }

  async function handleVerify(event) {
    event.preventDefault();
    setVerifyStatus("loading");
    setVerifyError("");
    try {
      await api.connectVerify(roleArn.trim());
      navigate("/dashboard");
    } catch (err) {
      setVerifyStatus("error");
      setVerifyError(err.message);
    }
  }

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

      <main className="container" style={{ maxWidth: 640, paddingTop: 24, paddingBottom: 96 }}>
        <div className="stack gap-sm" style={{ marginBottom: 40 }}>
          <h1 className="text-h2">Connect your account</h1>
          <p className="text-lede">Two steps. About two minutes, most of it AWS's.</p>
        </div>

        <div className="stack gap-lg">
          <div className="step">
            <div className="index">1</div>
            <div className="stack gap-sm">
              <h3 className="text-h3">Create the read-only role</h3>
              <p className="text-muted">
                This opens AWS CloudFormation in a new tab with a role template already filled
                in. It grants BillGuard permission to look at your account — never to change
                anything.
              </p>
              <div>
                <button
                  className="btn btn-primary"
                  onClick={handleOpenCloudFormation}
                  disabled={initStatus === "loading"}
                >
                  {initStatus === "loading" ? "Preparing…" : "Open CloudFormation"}
                </button>
              </div>
              {initStatus === "done" && (
                <p className="text-small text-faint">
                  Didn't open?{" "}
                  <a href={quickCreateUrl} target="_blank" rel="noopener noreferrer">
                    Open it here
                  </a>
                  .
                </p>
              )}
              {initStatus === "error" && <div className="error-banner">{initError}</div>}
            </div>
          </div>

          <div className="step">
            <div className="index">2</div>
            <div className="stack gap-sm" style={{ width: "100%" }}>
              <h3 className="text-h3">Paste the role's ARN</h3>
              <p className="text-muted">
                Once the stack finishes (usually under a minute), open its Outputs tab, copy{" "}
                <code>RoleArn</code>, and paste it here.
              </p>
              <form onSubmit={handleVerify} className="stack gap-sm">
                <div className="field">
                  <label htmlFor="roleArn">Role ARN</label>
                  <input
                    id="roleArn"
                    type="text"
                    placeholder="arn:aws:iam::123456789012:role/BillGuardReadOnly"
                    value={roleArn}
                    onChange={(e) => setRoleArn(e.target.value)}
                    required
                  />
                </div>
                <div>
                  <button
                    type="submit"
                    className="btn btn-primary"
                    disabled={verifyStatus === "loading" || !roleArn.trim()}
                  >
                    {verifyStatus === "loading" ? "Verifying…" : "Verify and connect"}
                  </button>
                </div>
                {verifyStatus === "error" && <div className="error-banner">{verifyError}</div>}
              </form>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
