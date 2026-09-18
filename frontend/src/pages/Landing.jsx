import { Link } from "react-router-dom";

import { useTickingValue } from "../hooks/useTickingValue.js";

const RESOURCE_TYPES = [
  "EC2 instances, running or stopped",
  "Unattached EBS volumes",
  "Elastic IPs with nothing attached",
  "NAT Gateways",
  "Load balancers, classic or v2",
  "RDS databases",
  "OpenSearch domains",
  "SageMaker endpoints and notebooks",
  "EKS clusters",
];

function formatInr(amount) {
  return amount.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Landing() {
  // A concrete example, not a global claim: ₹10.56/day since this Elastic
  // IP was found 4 days ago, ticking up live (accelerated for effect) —
  // dramatizing the one thing this whole product is about.
  const cost = useTickingValue(10.56 * 4, 10.56 / 14);

  return (
    <div className="page">
      <header className="container">
        <div className="topbar">
          <div className="wordmark">
            BillGuard<span className="dot">.</span>
          </div>
          <Link to="/connect" className="btn btn-outline">
            Sign in
          </Link>
        </div>
      </header>

      <main className="container" style={{ paddingBottom: 96 }}>
        <section className="hero-stage">
          <h1 className="text-hero">It's still running the meter.</h1>
          <p className="text-lede">
            Hackathon demos end. Free-tier trials expire. The test database, the spare Elastic
            IP, the notebook you spun up at 2am — none of them know that. BillGuard checks every
            region of your AWS account, once a day, and tells you exactly what's still costing
            money.
          </p>

          <div className="hero-finding">
            <div className="kind">
              <span className="live-dot" />
              Unassociated Elastic IP · ap-south-1
            </div>
            <div className="cost">
              ₹{formatInr(cost)}
              <span className="unit">and counting</span>
            </div>
            <div className="meta">
              <span>13.204.175.86</span>
              <span>found 4 days ago</span>
              <span>₹10.56 / day</span>
            </div>
          </div>

          <div className="hero-actions">
            <Link to="/connect" className="btn btn-primary">
              Connect your AWS account
            </Link>
          </div>
        </section>

        <hr className="divider" />

        <section
          className="stack gap-md"
          style={{ padding: "72px 0", maxWidth: 720, marginLeft: "auto", marginRight: "auto" }}
        >
          <h2 className="text-h2">How it works</h2>
          <p className="text-lede">
            You connect a role that can only read — never start, stop, or delete anything.
            BillGuard uses it to check every enabled region, once a day, for resources that are
            still billing. Anything it finds comes with the exact region, the estimated cost per
            day, and the console steps to remove it. Nothing gets touched without you.
          </p>
        </section>

        <hr className="divider" />

        <section
          className="stack gap-md"
          style={{ padding: "72px 0", maxWidth: 720, marginLeft: "auto", marginRight: "auto" }}
        >
          <h2 className="text-h2">What it looks for</h2>
          <ul
            className="text-muted"
            style={{
              columns: 2,
              columnGap: 40,
              margin: 0,
              padding: 0,
              listStyle: "none",
              fontSize: "1.05rem",
            }}
          >
            {RESOURCE_TYPES.map((item) => (
              <li key={item} style={{ marginBottom: 14, breakInside: "avoid" }}>
                {item}
              </li>
            ))}
          </ul>
        </section>

        <hr className="divider" />

        <section
          className="stack gap-sm"
          style={{ padding: "72px 0", maxWidth: 640, marginLeft: "auto", marginRight: "auto" }}
        >
          <h2 className="text-h2">Read-only. Revocable anytime.</h2>
          <p className="text-lede">
            The role BillGuard uses lists an exact, narrow set of permissions — every one of them
            a <code>Describe</code> or <code>List</code> call. There is no permission to create,
            modify, or delete anything in your account. Disconnect whenever you want by deleting
            one CloudFormation stack; access ends immediately.
          </p>
        </section>
      </main>

      <footer className="container text-small text-faint" style={{ paddingBottom: 32, textAlign: "center" }}>
        Built for hackathon builders and students who'd rather not find out the hard way.
      </footer>
    </div>
  );
}
