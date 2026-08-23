# AI Cloud Cost Detective (AWS + Claude)

An AI-powered tool that scans an AWS region using the AWS CLI, detects cost
waste and misconfigurations, and generates a Markdown report with specific,
actionable fix commands.

This is a scoped-down, AWS-native rebuild of [Abhishek Veeramalla's AI-Cloud-Cost-Detective](https://github.com/iam-veeramalla/AI-Cloud-Cost-Detective),
which used Azure CLI + a full React/FastAPI/PostgreSQL/JWT stack with the
OpenAI API. This version:

- Targets **AWS** instead of Azure (matches AWS Certified Cloud Practitioner
  background and target DevOps/Cloud roles)
- Uses the **Claude API** instead of OpenAI
- Is a **single-user CLI tool**, not a multi-tenant web app — no auth/JWT/
  WebSockets/database, since there's only one user (whoever runs it) and no
  need to authenticate sessions for a local script
- Uses a **read-only IAM user** for all AWS access — the tool can only
  describe/list resources, never modify or delete anything

## What It Detects

- **Over-provisioned resources** — EC2/RDS instances larger than the
  workload appears to need
- **Unused/orphaned resources** — unattached EBS volumes, unassociated
  Elastic IPs, load balancers with no healthy targets
- **Misconfigurations** — resources running 24/7 without Reserved
  Instances/Savings Plans, missing auto-shutdown patterns
- **Storage & logging costs** — S3 buckets with no lifecycle policy
- **Cost breakdown** — top AWS services by spend, from Cost Explorer

## Tech Stack

- Python 3
- [Anthropic Claude API](https://docs.claude.com) (`anthropic` SDK)
- AWS CLI (read-only access, called via `subprocess`)

## Security

This tool is built around **least-privilege access**:

- All AWS access uses a dedicated IAM user with a **read-only policy**
  (e.g., `ec2:Describe*`, `rds:Describe*`, `s3:ListAllMyBuckets`,
  `ce:GetCostAndUsage`) — it cannot create, modify, or delete anything
- AWS credentials are configured via a named CLI profile, never hardcoded
- No credentials, tokens, or account data are committed to this repo

## Setup

```bash
pip install -r requirements.txt
```

Configure a read-only AWS CLI profile:

```bash
aws configure --profile cost-detective-readonly
```

Set your Claude API key:

```bash
# Windows (cmd)
set ANTHROPIC_API_KEY=your_key_here

# macOS/Linux
export ANTHROPIC_API_KEY=your_key_here
```

## Usage

```bash
python cost_detective.py --region ap-south-1 --profile cost-detective-readonly
```

This will:
- Run read-only AWS CLI commands across EC2, EBS, EIPs, ELB, RDS, S3, and
  Cost Explorer
- Send the collected data + assessment prompt to Claude
- Print the report to the terminal
- Save it to `cost_reports/cost_report_<region>_<timestamp>.md`

## Project Structure

```
.
├── prompt.md              # The cost-analysis prompt Claude follows
├── cost_detective.py      # Collects AWS CLI data and calls the Claude API
├── requirements.txt       # Python dependency (anthropic)
└── cost_reports/          # Generated reports (git-ignored)
```

## Why This Project

Built to combine two things directly relevant to Cloud/DevOps roles — AWS
resource management and AI-assisted tooling — into something that produces
an actionable cost-savings report instead of a generic chatbot wrapper.

## Credits

Concept inspired by [iam-veeramalla/AI-Cloud-Cost-Detective](https://github.com/iam-veeramalla/AI-Cloud-Cost-Detective).
