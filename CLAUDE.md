# CLAUDE.md — BillGuard project context

This file gives Claude Code the context for this repo. Read it before making changes.

## What we're building

**BillGuard** (working name): a web app that catches forgotten AWS resources before they turn into a surprise bill or silently burn a user's free credits.

A user connects their AWS account with one click (read-only cross-account IAM role). BillGuard scans all enabled regions daily, finds billable leftovers, and shows what it is, which region, estimated ₹/day cost, and step-by-step delete instructions. New findings trigger an email alert.

**Target users:** students and beginner builders (hackathon participants, college cloud courses), especially those on AWS's paid account plan or older accounts, and free-plan users who can lose credits. Pitch framing: "don't lose money *or* credits to things you forgot."

## Hackathon context

- Event: *First Commit*, Bharat Builds Tour (AWS + WeMakeDevs), online Sept 17–20, 2026.
- Team **NotAISlop**: Satvik Golla (backend/infra), Madhu (frontend/design).
- Track: **Ship It** — must be deployed live on AWS with a URL; architecture and cost decisions are scored. Best UI is judged separately.
- Judging: idea & impact, built on AWS, learning, execution ("one working feature beats five that almost work"), 3-minute recorded demo video (no live demo).
- Goal: **real users by Saturday night**, real traction numbers in the demo video. Submit Sunday with buffer.

## Hard rules

- **Never modify or delete anything in a user's AWS account.** Scan and report only. No auto-delete this weekend.
- **User-side role uses an explicit read-only permission list.** No `ReadOnlyAccess` or other broad managed policies in the shipped template.
- **Every connection requires a unique per-user ExternalId** (prevents confused deputy). The user role's trust policy trusts only the scanner Lambda's role ARN, not the whole platform account.
- **Never pass temporary credentials through Step Functions state.** Each Lambda calls `sts:AssumeRole` itself.
- **Never commit secrets.** AWS keys live in `~/.aws/credentials`. No keys in code, `.env` files committed, logs, or screenshots.
- **Catch errors per region.** A disabled region or AccessDenied marks the region skipped; it must not fail the whole scan.
- **Cost Explorer is called at most once per user per day** (~$0.01 per call). Resource Describe calls are free.
- Keep platform cost near zero: serverless only, scales to zero.

## Architecture

```
Browser → Amplify (React/Vite) + Cognito
       → API Gateway (HTTP API, Cognito JWT authorizer)
       → API Lambdas → DynamoDB (single table)

EventBridge Scheduler (daily, 9 AM IST) → Step Functions: ScanAll
   → query connected users → Map over users → Step Functions: ScanAccount

ScanAccount (also started by POST /scan):
   1. Lambda: AssumeRole → ec2:DescribeRegions
   2. Map over regions (parallel) → Scanner Lambda per region (assumes role itself)
   3. Lambda: Cost Explorer month-to-date spend (once)
   4. Lambda: diff vs previous findings → new / still running / resolved
   5. New findings → SES email

User's account: IAM role "BillGuardReadOnly" created by user-role/billguard-role.yaml
```

### Connect flow
1. `POST /connect/init` → generate ExternalId, save profile as `pending`, return CloudFormation quick-create URL with params `ExternalId` and `TrustedPrincipalArn` (scanner role ARN).
2. User creates stack, copies `RoleArn` output, pastes it in the app.
3. `POST /connect/verify` → test AssumeRole with stored ExternalId, confirm account ID from ARN matches, set `connected`, start first scan.
4. Stretch: automatic RoleArn callback (no copy-paste).

### Resources to scan
EC2 instances (running/stopped), unattached EBS volumes, unassociated Elastic IPs, NAT Gateways, load balancers (ELBv2 + classic), RDS instances, OpenSearch domains, SageMaker endpoints and notebook instances, EKS clusters.

Cost estimates come from a **hardcoded price table** (USD/hour per type, converted to INR) — not the Pricing API.

### User-role permissions (explicit list)
```
ec2:DescribeRegions, ec2:DescribeInstances, ec2:DescribeVolumes,
ec2:DescribeAddresses, ec2:DescribeNatGateways,
elasticloadbalancing:DescribeLoadBalancers,
rds:DescribeDBInstances,
es:ListDomainNames, es:DescribeDomains,
sagemaker:ListEndpoints, sagemaker:ListNotebookInstances,
eks:ListClusters,
ce:GetCostAndUsage
```
Add actions here only when a scanner check needs them.

## API contract

| Method | Path | Description |
|---|---|---|
| POST | `/connect/init` | Create ExternalId, return quick-create URL |
| POST | `/connect/verify` | Body `{ roleArn }`. Verify, mark connected, start scan |
| GET | `/findings` | Active + resolved findings for signed-in user |
| POST | `/scan` | Start ScanAccount; rate limit once per 10 min |
| GET | `/scan/latest` | Latest scan status + summary |
| DELETE | `/account` | Disconnect, delete all user data, remind to delete stack |

Madhu builds the UI against fake JSON matching these responses, so keep response shapes stable. If you change one, update this file.

## Data model (DynamoDB single table: PK / SK)

| PK | SK | Attributes |
|---|---|---|
| `USER#<cognitoSub>` | `PROFILE` | email, awsAccountId, roleArn, externalId, status (`pending`/`connected`/`error`), lastScanAt, lastManualScanAt |
| `USER#<cognitoSub>` | `FINDING#<region>#<resourceId>` | type, name, region, estDailyCostInr, firstSeen, lastSeen, status (`active`/`resolved`) |
| `USER#<cognitoSub>` | `SCAN#<isoTimestamp>` | regionsScanned, regionsSkipped, findingsCount, monthToDateSpendUsd |
| `STATS` | `GLOBAL` | accountsConnected, resourcesFound |

GSI on profile `status` so ScanAll can list connected users.

## Repo layout

```
cloudbill/
├── CLAUDE.md
├── README.md
├── .gitignore
├── backend/       # SAM template.yaml + Lambda functions (Python)
├── frontend/      # React (Vite) app, deployed via Amplify
└── user-role/     # billguard-role.yaml — CloudFormation template users deploy
```

## Tech & conventions

- **Backend:** Python, boto3, Lambda runtime **`python3.13`** (matches local Python 3.13.2). Infra defined in AWS SAM.
- **Frontend:** React + Vite, Amplify Hosting, Amplify Auth (Cognito).
- **Region:** platform runs in `ap-south-1` (Mumbai). Cost Explorer uses its global endpoint (`us-east-1`).
- Small, readable functions; one Lambda per API route or scan step.
- Log with structured JSON to CloudWatch; never log credentials or ExternalIds.
- Prefer boto3 paginators for all List/Describe calls.

## Dev environment

- Windows 11, `cmd` terminal. Project folder: `C:\Users\chinn\Desktop\cloudbill`.
- Installed: AWS CLI 2.36.47, SAM CLI 1.166.2, Python 3.13.2, Node 22.17.1, Git 2.51.2.
- Python venv: `.venv` (activate with `.venv\Scripts\activate`).
- AWS CLI profiles:
  - `platform` — our AWS account (runs BillGuard), IAM user `Satvikcli` with AdministratorAccess.
  - `testuser` — second account acting as a "user" (may be Madhu's account; if so, she creates the role and shares only the role ARN, no keys).
- Use commands that work in Windows `cmd` (no `#` comments, no bash-only syntax) unless told otherwise.

## Current status

- [x] Tools installed and verified
- [x] IAM CLI user created in platform account
- [ ] `platform` profile configured and verified (`aws sts get-caller-identity --profile platform`)
- [ ] Test account ready (profile or role ARN from Madhu)
- [ ] Repo initialized: git, folders, venv, boto3, .gitignore, README
- [ ] Budget alert ($5) on both accounts
- [ ] SES production access requested; Cost Explorer enabled in test account
- [ ] Bait resource in test account: one unattached Elastic IP (release after hackathon)

## Next tasks (in order)

1. **Prove cross-account access:** create a test role in the test account trusting the platform account with ExternalId; run `aws sts assume-role` from `platform`; confirm a wrong ExternalId fails.
2. Write `user-role/billguard-role.yaml` (parameters: `ExternalId`, `TrustedPrincipalArn`; output: `RoleArn`).
3. Local scanner script: assume role → list unassociated Elastic IPs in one region → print. Must find the bait EIP.
4. Extend scanner to all resource types, one region, with price table.
5. SAM backend: DynamoDB table, `/connect/init`, `/connect/verify`, `/findings`.
6. Step Functions ScanAccount (Map over regions) + `/scan`, `/scan/latest`.
7. ScanAll + EventBridge Scheduler + SES alerts + STATS row.
8. Deploy, share link Saturday evening, fix real-user bugs Sunday morning.

## Out of scope for the weekend

Auto-delete/remediation, multiple AWS accounts per user, AWS Organizations support, charts/graphs, Pricing API, other clouds.

## Stretch (only after core is deployed)

Automatic RoleArn callback, Bedrock plain-language explanations, post-hackathon cleanup checklist, Telegram alerts.
