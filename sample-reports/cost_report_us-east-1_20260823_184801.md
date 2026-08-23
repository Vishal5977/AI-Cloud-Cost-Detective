# AWS Cloud Cost Detective — Optimization & Waste Assessment

## Executive Summary

```text
REGION REVIEWED: us-east-1
ESTIMATED MONTHLY WASTE: Not calculable from available data
  (Total observed account spend over the review window is ~$0.45,
  and no confirmed idle/orphaned billable resources — EC2, EBS, EIP,
  ELB, RDS — were found in the scan. Any "waste" here is speculative
  at these dollar amounts.)
TOTAL FINDINGS: 4
CRITICAL: 0   HIGH: 0   MEDIUM: 1   LOW: 3
```

**Context:** This account has an extremely small footprint. `describe-instances`, `describe-volumes`, `describe-addresses`, `describe-load-balancers`, and `describe-db-instances` all returned empty result sets. The only live resources found in-scope were **2 S3 buckets**. Cost Explorer confirms this — total spend for the reviewed ~30-day window is approximately **$0.45**, meaning this is a low/no-traffic or largely idle account (dev/sandbox, or a workload that has since been decommissioned). Findings below are therefore mostly about *data-completeness gaps* and *small anomalies* rather than large waste — there is simply not enough active infrastructure to have generated significant waste.

---

## Findings Table

---

```text
Resource ID / Name: N/A (no matching EC2 instance/volume/NAT Gateway/EIP found)
Resource Type: EC2 - Other (Cost Explorer line item)
Category: Unused / Orphaned (unconfirmed — requires investigation)
Issue: Cost Explorer shows an "EC2 - Other" charge of $0.2134 over the Aug 1–23
       window (and a negligible $0.0000005 in the prior period), but
       describe-instances, describe-volumes, and describe-addresses all
       returned empty for this region. "EC2 - Other" typically bills for
       NAT Gateways, EBS snapshots, VPN connections, or data transfer —
       none of which were queried directly in this scan. This is a
       mismatch between billed service and resources actually found.
Estimated Monthly Impact: ~$0.21–$0.29/month (small, but source unconfirmed)
Severity: Medium
Recommended Fix: Investigate the true source of this charge before assuming
       it's benign — check for orphaned EBS snapshots, idle NAT Gateways,
       or VPC endpoints that weren't covered by this scan.
Fix Command:
  aws ec2 describe-snapshots --owner-ids self --region us-east-1
  aws ec2 describe-nat-gateways --region us-east-1
  aws ec2 describe-vpc-endpoints --region us-east-1
  aws ce get-cost-and-usage --time-period Start=2026-08-01,End=2026-08-23 \
    --granularity DAILY --metrics "UnblendedCost" \
    --filter '{"Dimensions":{"Key":"SERVICE","Values":["EC2 - Other"]}}' \
    --group-by Type=DIMENSION,Key=USAGE_TYPE
```

---

```text
Resource ID / Name: N/A (no ECR repositories were pulled in this scan)
Resource Type: Amazon ECR (Cost Explorer line item)
Category: Storage & Logging / Misconfiguration (unconfirmed — requires investigation)
Issue: Cost Explorer shows $0.1492 in ECR charges over the Aug 1–23 window
       (up from $0 in the prior period). No `describe-repositories` /
       `list-images` data was collected, so it's not possible to confirm
       whether this is active image storage or old/untagged images
       accumulating without a lifecycle policy.
Estimated Monthly Impact: ~$0.15–$0.20/month
Severity: Low
Recommended Fix: Audit ECR repositories for unused/untagged image layers and
       apply lifecycle policies to expire old images automatically.
Fix Command:
  aws ecr describe-repositories --region us-east-1
  aws ecr list-images --repository-name <repo-name> --region us-east-1 \
    --filter tagStatus=UNTAGGED
  aws ecr put-lifecycle-policy --repository-name <repo-name> --region us-east-1 \
    --lifecycle-policy-text file://ecr-lifecycle-policy.json
```

---

```text
Resource ID / Name: ekadantha-embroidery-designs
Resource Type: S3 Bucket
Category: Storage & Logging
Issue: Bucket name/usage pattern ("designs") suggests it may hold long-lived
       binary assets. Lifecycle configuration was NOT queried in this scan,
       so it cannot be confirmed whether a lifecycle policy exists. This is
       a data gap, not a confirmed misconfiguration — flagging for
       verification per FinOps best practice, since S3 buckets very
       commonly lack lifecycle rules by default.
Estimated Monthly Impact: Unknown (current S3 spend across both buckets is
       only ~$0.02/month, so impact is currently negligible, but risk grows
       with data volume)
Severity: Low
Recommended Fix: Verify lifecycle configuration exists; if not, add rules to
       transition older objects to S3-IA/Glacier and/or expire abandoned
       upload artifacts.
Fix Command:
  aws s3api get-bucket-lifecycle-configuration --bucket ekadantha-embroidery-designs
  aws s3api put-bucket-lifecycle-configuration --bucket ekadantha-embroidery-designs \
    --lifecycle-configuration file://lifecycle-policy.json
```

---

```text
Resource ID / Name: ekadantha-embroidery-upload
Resource Type: S3 Bucket
Category: Storage & Logging
Issue: Same as above — this bucket's name ("upload") strongly suggests it
       receives inbound customer/user files, which are classic candidates
       for accumulating over time without expiration rules. Lifecycle
       status was not verifiable from the data provided.
Estimated Monthly Impact: Unknown (negligible today; grows with usage)
Severity: Low
Recommended Fix: Verify lifecycle configuration; if absent, add rules to
       expire/transition stale uploads (e.g., incomplete multipart uploads,
       temp files older than 30–90 days).
Fix Command:
  aws s3api get-bucket-lifecycle-configuration --bucket ekadantha-embroidery-upload
  aws s3api put-bucket-lifecycle-configuration --bucket ekadantha-embroidery-upload \
    --lifecycle-configuration file://lifecycle-policy.json
  # Also worth checking for abandoned multipart uploads, a common hidden S3 cost:
  aws s3api list-multipart-uploads --bucket ekadantha-embroidery-upload
```

---

## Cost Breakdown Summary

*(Combined totals across both Cost Explorer periods: 2026-07-24 → 2026-08-23, ≈30 days, total ≈ $0.4536)*

```text
| Service                          | Approx. Monthly Cost | % of Total |
|-----------------------------------|-----------------------|------------|
| EC2 - Other                       | $0.2134               | 47.0%      |
| Amazon ECR                        | $0.1492               | 32.9%      |
| Tax                                | $0.0700               | 15.4%      |
| Amazon S3                         | $0.0202               | 4.5%       |
| AWS Lambda                        | $0.0007               | 0.16%      |
| AWS Secrets Manager                | $0.00002              | ~0.0%      |
| All other services (Glue, KMS,    | $0.0000               | 0.0%       |
| EC2-Compute, VPC, CloudWatch,      |                       |            |
| SNS, SQS, CloudFront)              |                       |            |
```

No single service is disproportionately expensive in absolute terms — the entire account spend is under $0.50/month — but **EC2-Other and ECR together represent ~80% of spend despite zero EC2/ECR resources being visible in the resource scan**, which is the core anomaly worth investigating (Findings 1 & 2 above).

---

## Top 5 Recommended Actions

Ranked by risk/severity (savings amounts are too small to be a meaningful ranking basis given total spend of $0.45/month):

1. **[Medium]** Investigate the source of "EC2 - Other" charges (snapshots, NAT Gateway, VPN, data transfer) since no matching EC2/EBS/EIP resources were found in the direct resource scan.
2. **[Low]** Audit ECR repositories for old/untagged images and apply a lifecycle policy — cost is trending upward from $0 to $0.15 between the two periods.
3. **[Low]** Verify lifecycle configuration on `ekadantha-embroidery-designs` — confirm whether cold-storage transition or expiration rules exist.
4. **[Low]** Verify lifecycle configuration on `ekadantha-embroidery-upload`, and check for abandoned multipart uploads, which are a common invisible S3 cost.
5. **[Informational]** Re-run this review with Cost Explorer usage-type-level detail (`--group-by Type=DIMENSION,Key=USAGE_TYPE`) once the account has meaningful compute activity, since current spend is too low to reliably detect right-sizing or RI/Savings Plan opportunities.

---

## Final Notes

* **No EC2 instances found** — Over-Provisioning and RI/Savings Plan analysis (Category 1 & 3) could not be performed; there is nothing running to right-size or commit to.
* **No EBS volumes found** — no orphaned/`available`-state volumes to report (Category 2).
* **No Elastic IPs found** — no unattached EIP charges to report (Category 2).
* **No Load Balancers found** — no zero-target ELB waste to report (Category 2).
* **No RDS instances found** — no idle/stopped database or Multi-AZ misconfiguration findings possible (Category 1 & 3).
* **S3 lifecycle policies could not be verified** — `get-bucket-lifecycle-configuration` was not run against either bucket in the provided data, so "no lifecycle policy" is **not** asserted as confirmed fact, only flagged as an unverified gap worth checking.
* **ECR repository inventory was not collected** — the $0.15 ECR charge cannot be attributed to specific repositories/images without further data.
* **NAT Gateways, VPC Endpoints, and EBS Snapshots were not directly queried** in this scan — these are the most likely explanations for the "EC2 - Other" charge and should be checked using the commands provided in Finding 1.
* Given the account's total spend is under $1/month, this appears to be either a **new/sandbox account** or a **recently decommissioned workload** — the priority here is verifying no hidden resources are quietly accumulating (snapshots, NAT gateways, ECR images) rather than right-sizing active infrastructure, since none exists in this scan.