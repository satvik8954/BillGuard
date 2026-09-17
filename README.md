# BillGuard

**Catch forgotten AWS resources before they turn into a surprise bill.**

Built by team **NotAISlop** for *First Commit*, Bharat Builds Tour (Sept 17–20, 2026), Ship It track.

> 🚧 Work in progress — being built during the hackathon weekend.

---

## The problem

Students create AWS accounts for hackathons and courses, try things out, and forget to turn them off. A NAT Gateway, an idle RDS database, or an unattached Elastic IP keeps charging every day, often in a region they never open. They find out when a bill hits their debit card, or when their free credits quietly run out and the account closes mid-project.

## The solution

Connect your AWS account in one click with **read-only** access. BillGuard scans every region daily, finds anything still running and costing money, and tells you in plain language:

- **what** it is and **where** (resource + region)
- **how much** it costs per day (in ₹)
- **how to delete** it, step by step

New leftovers trigger an email alert. BillGuard never modifies or deletes anything in your account.

---

## How it works

```
User's browser
     │
     ▼
Amplify (React) ── Cognito (login)
     │
     ▼
API Gateway (HTTP API, JWT auth) ──► API Lambdas ──► DynamoDB
                                          │              ▲
                                    "Scan now"           │
                                          ▼              │
EventBridge Scheduler ──► Step Functions: ScanAll        │
       (daily)                     │                     │
                                   ▼                     │
                     Step Functions: ScanAccount ────────┤
                                   │ Map over regions    │
                                   ▼                     │
                          Scanner Lambda ×N ─────────────┘──► SES alert
                                   │
                    sts:AssumeRole + ExternalId
                                   ▼
                  ┌── User's AWS account ──────────────┐
                  │  IAM role: BillGuardReadOnly       │
                  │  Describe*/List* + Cost Explorer   │
                  └────────────────────────────────────┘
```

### Connecting an account
1. User signs in and clicks **Connect AWS**.
2. Backend generates a unique **ExternalId** and returns a CloudFormation quick-create link.
3. The stack creates a read-only role in the user's account that trusts only BillGuard's scanner role and requires that ExternalId.
4. User pastes the Role ARN back; backend verifies with a test `AssumeRole` and starts the first scan.

### Scanning
1. EventBridge Scheduler starts `ScanAll` once a day (or the user clicks **Scan now**).
2. `ScanAccount` lists enabled regions and scans them **in parallel**.
3. Each regional Lambda assumes the role itself (credentials never pass through workflow state) and checks for billable resources. Failures are caught per region.
4. Cost Explorer is called once per user per day for month-to-date spend.
5. Findings are diffed against the last scan: **new**, **still running**, or **resolved**. New findings trigger an email.

### What we look for
EC2 instances · unattached EBS volumes · unused Elastic IPs · NAT Gateways · load balancers · RDS databases · OpenSearch domains · SageMaker endpoints and notebooks · EKS clusters

---

## Security

- **Read-only, explicit permissions.** The user-side role lists every allowed action; no broad managed policies. See [`user-role/billguard-role.yaml`](user-role/billguard-role.yaml).
- **ExternalId per user** prevents the confused-deputy problem (someone connecting another person's account).
- **Trust is scoped to the scanner role**, not our whole AWS account.
- **Revoke anytime** by deleting the CloudFormation stack in your account. Disconnecting in the app deletes all your stored data.

---

## Tech stack

| Layer | Services |
|---|---|
| Frontend | AWS Amplify Hosting, React (Vite), Amazon Cognito |
| API | Amazon API Gateway (HTTP API), AWS Lambda (Python 3.12) |
| Orchestration | AWS Step Functions, Amazon EventBridge Scheduler |
| Data | Amazon DynamoDB (single table) |
| Cross-account | AWS STS, IAM, AWS CloudFormation |
| Cost & alerts | AWS Cost Explorer API, Amazon SES |
| IaC | AWS SAM |
| Monitoring | Amazon CloudWatch |

---

## Repository structure

```
billguard/
├── backend/          # SAM template + Lambda functions
├── frontend/         # React app (Amplify)
├── user-role/        # CloudFormation template users deploy in their account
└── README.md
```

---

## API

| Method | Path | Description |
|---|---|---|
| POST | `/connect/init` | Create ExternalId, return CloudFormation quick-create URL |
| POST | `/connect/verify` | Verify Role ARN with a test AssumeRole, start first scan |
| GET | `/findings` | Active and resolved findings for the signed-in user |
| POST | `/scan` | Start a scan (rate limited to once per 10 minutes) |
| GET | `/scan/latest` | Status and summary of the latest scan |
| DELETE | `/account` | Disconnect and delete all stored data |

## Data model (DynamoDB, single table)

| PK | SK | Attributes |
|---|---|---|
| `USER#<id>` | `PROFILE` | email, awsAccountId, roleArn, externalId, status, lastScanAt |
| `USER#<id>` | `FINDING#<region>#<resourceId>` | type, name, estDailyCostInr, firstSeen, lastSeen, status |
| `USER#<id>` | `SCAN#<timestamp>` | regionsScanned, regionsSkipped, findingsCount, monthToDateSpend |
| `STATS` | `GLOBAL` | accountsConnected, resourcesFound |

---

## Local development

### Prerequisites
- AWS CLI v2, AWS SAM CLI
- Python 3.12, Node.js LTS, Git
- Two AWS accounts: a **platform** account and a **test user** account

### Setup

```bash
git clone <repo-url>
cd billguard

# Python environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install boto3

# AWS profiles
aws configure --profile platform
aws configure --profile testuser

# Confirm both profiles point to different accounts
aws sts get-caller-identity --profile platform
aws sts get-caller-identity --profile testuser
```

> Never commit AWS keys. Credentials live in `~/.aws/credentials`, outside the repo.

### Test cross-account access

In the **testuser** account, create a role that trusts the platform account and requires an external ID, then:

```bash
aws sts assume-role \
  --role-arn arn:aws:iam::<TESTUSER_ACCOUNT_ID>:role/BillGuardTest \
  --role-session-name test \
  --external-id <EXTERNAL_ID> \
  --profile platform
```

Temporary credentials in the response mean it works. A wrong external ID should fail.

### Deploy the backend

```bash
cd backend
sam build
sam deploy --guided --profile platform
```

### Run the frontend

```bash
cd frontend
npm install
npm run dev
```

---

## Roadmap

**Weekend (core)**
- [ ] User-side CloudFormation role template
- [ ] Connect flow (init + verify)
- [ ] Scanner for all listed resource types
- [ ] Parallel multi-region scan with Step Functions
- [ ] Findings dashboard with ₹/day estimates and delete instructions
- [ ] Daily schedule + email alerts
- [ ] Deployed live on AWS

**Stretch**
- [ ] Automatic Role ARN callback (no copy-paste)
- [ ] Plain-language explanations with Amazon Bedrock
- [ ] Post-hackathon cleanup checklist
- [ ] Telegram alerts

---

## Team NotAISlop

- **Satvik Golla** — backend & infrastructure
- **Madhu** — frontend & design
