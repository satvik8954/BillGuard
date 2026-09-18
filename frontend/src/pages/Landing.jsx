import { Link } from "react-router-dom";

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

export default function Landing() {
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
        <section
          className="hero-grid"
          style={{
            paddingTop: 56,
            paddingBottom: 64,
          }}
        >
          <div className="stack gap-md">
            <h1 className="text-hero">It's still running the meter.</h1>
            <p className="text-lede">
              Hackathon demos end. Free-tier trials expire. The test database, the spare Elastic
              IP, the notebook you spun up at 2am — none of them know that. BillGuard checks every
              region of your AWS account once a day and tells you exactly what's still costing
              money, and how to turn it off.
            </p>
            <div>
              <Link to="/connect" className="btn btn-primary">
                Connect your AWS account
              </Link>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "center" }}>
            <div className="hero-finding">
              <div className="row-top">
                <span className="kind">
                  <span className="pulse-dot" style={{ marginRight: 8 }} />
                  Unassociated Elastic IP
                </span>
              </div>
              <div className="cost">
                ₹10.56<span>/ day</span>
              </div>
              <div className="meta">
                <span>ap-south-1</span>
                <span>13.204.175.86</span>
                <span>found 4 days ago</span>
              </div>
            </div>
          </div>
        </section>

        <hr className="divider" />

        <section className="stack gap-md" style={{ padding: "56px 0", maxWidth: 720 }}>
          <h2 className="text-h2">How it works</h2>
          <p className="text-lede">
            You connect a role that can only read — never start, stop, or delete anything.
            BillGuard uses it to check every enabled region, once a day, for resources that are
            still billing. Anything it finds comes with the exact region, the estimated cost per
            day, and the console steps to remove it. Nothing gets touched without you.
          </p>
        </section>

        <hr className="divider" />

        <section className="stack gap-md" style={{ padding: "56px 0" }}>
          <h2 className="text-h2">What it looks for</h2>
          <ul
            className="text-muted"
            style={{
              columns: 2,
              columnGap: 40,
              margin: 0,
              padding: 0,
              listStyle: "none",
              maxWidth: 640,
            }}
          >
            {RESOURCE_TYPES.map((item) => (
              <li key={item} style={{ marginBottom: 12, breakInside: "avoid" }}>
                {item}
              </li>
            ))}
          </ul>
        </section>

        <hr className="divider" />

        <section className="stack gap-sm" style={{ padding: "56px 0", maxWidth: 640 }}>
          <h2 className="text-h2">Read-only. Revocable anytime.</h2>
          <p className="text-lede">
            The role BillGuard uses lists an exact, narrow set of permissions — every one of them
            a <code>Describe</code> or <code>List</code> call. There is no permission to create,
            modify, or delete anything in your account. Disconnect whenever you want by deleting
            one CloudFormation stack; access ends immediately.
          </p>
        </section>
      </main>

      <footer className="container text-small text-faint" style={{ paddingBottom: 32 }}>
        Built for hackathon builders and students who'd rather not find out the hard way.
      </footer>
    </div>
  );
}
