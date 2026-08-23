# AWS Cloud Cost Detective — Optimization & Waste Assessment

## Executive Summary

```text
REGION REVIEWED: ap-south-1
ESTIMATED MONTHLY WASTE: Not calculable from available data (total spend ~$0.45 over the review period; no idle/orphaned billable resources found)
TOTAL FINDINGS: 3
CRITICAL: 0   HIGH: 0   MEDIUM: 1   LOW: 2
```

**Overall observation:** This account/region shows essentially no compute, storage-volume, or database footprint. EC2, EBS, EIP, ELB, and RDS all returned empty result sets. Total spend across the ~30-day window is approximately **$0.45 USD**, driven almost entirely by ECR, EC2-Other (likely NAT Gateway/data transfer residuals), S3, and Tax. There is **no evidence of over-provisioning, idle instances, or orphaned infrastructure** — because there is effectively no infrastructure currently provisioned in this region. The only actionable findings relate to the two S3 buckets lacking lifecycle policies.

---

## Findings Table

```text
Resource ID / Name: ekadantha-embroidery-designs
Resource Type: S3 Bucket
Category: Storage & Logging
Issue: No lifecycle policy detected in the provided data. If this bucket accumulates design files over time without transition/expiration rules, storage costs will grow unnecessarily as objects age in Standard storage.
Estimated Monthly Impact: Unknown (bucket size/object count not available from provided data)
Severity: Medium
Recommended Fix: Review bucket contents and access patterns; if objects are infrequently accessed after creation, apply a lifecycle rule to transition to Standard-IA/Glacier and/or expire old versions/incomplete multipart uploads.
Fix Command:
aws s3api get-bucket-lifecycle-configuration --bucket ekadantha-embroidery-designs --region ap-south-1
# (Returns error if none exists — confirms no policy is configured)
aws s3api put-bucket-lifecycle-configuration --bucket ekadantha-embroidery-designs --region ap-south-1 --lifecycle-configuration file://lifecycle.json
```

```text
Resource ID / Name: ekadantha-embroidery-upload
Resource Type: S3 Bucket
Category: Storage & Logging
Issue: No lifecycle policy detected in the provided data. This bucket name suggests it may receive uploaded files (potentially transient); without lifecycle rules, stale or abandoned uploads (including incomplete multipart uploads) accumulate cost indefinitely.
Estimated Monthly Impact: Unknown (bucket size/object count not available from provided data)
Severity: Medium
Recommended Fix: Verify whether uploaded objects need long-term retention. If uploads are temporary/staging in nature, add a lifecycle rule to expire objects after a defined period and abort incomplete multipart uploads after 7 days.
Fix Command:
aws s3api get-bucket-lifecycle-configuration --bucket ekadantha-embroidery-upload --region ap-south-1
aws s3api put-bucket-lifecycle-configuration --bucket ekadantha-embroidery-upload --region ap-south-1 --lifecycle-configuration file://lifecycle.json
```

```text
Resource ID / Name: EC2 - Other (Cost Explorer line item)
Resource Type: Cost Explorer Service Category (likely NAT Gateway, EBS snapshots, or data transfer — not attributable to a specific resource since EC2/EBS scans returned empty)
Category: Misconfiguration / Cost Breakdown Mismatch
Issue: "EC2 - Other" shows $0.213 in the second period despite EC2 instance and EBS volume scans returning zero resources. This is a mismatch worth investigating — it suggests either a resource in another AZ/state not captured by the scan (e.g., a NAT Gateway, VPC endpoint, or snapshot) or residual metered usage from a recently terminated resource.
Estimated Monthly Impact: ~$0.21–$0.30/month at current run-rate (small in absolute terms, but the mismatch itself is the finding)
Severity: Low
Recommended Fix: Investigate what specific resource/usage type is generating "EC2 - Other" charges before assuming the account is fully idle.
Fix Command:
aws ce get-cost-and-usage --time-period Start=2026-07-24,End=2026-08-23 --granularity DAILY --metrics UnblendedCost --filter '{"Dimensions":{"Key":"SERVICE","Values":["EC2 - Other"]}}' --group-by Type=DIMENSION,Key=USAGE_TYPE --region ap-south-1
aws ec2 describe-nat-gateways --region ap-south-1
aws ec2 describe-vpc-endpoints --region ap-south-1
aws ec2 describe-snapshots --owner-ids self --region ap-south-1
```

---

## Cost Breakdown Summary

*Based on combined totals from both Cost Explorer periods provided (2026-07-24 to 2026-08-23, partially estimated for the later period):*

```text
| Service                                   | Approx. Monthly Cost | % of Total |
|--------------------------------------------|----------------------|------------|
| Tax                                        | $0.0700              | 15.6%      |
| Amazon EC2 Container Registry (ECR)        | $0.1492              | 33.2%      |
| EC2 - Other                                | $0.2134              | 47.5%      |
| Amazon Simple Storage Service               | $0.0202              | 4.5%       |
| AWS Lambda                                  | $0.0007              | 0.2%       |
| AWS Secrets Manager                         | $0.00002             | <0.01%     |
| AWS Glue / KMS / CloudFront / SNS / SQS / VPC / CloudWatch | $0.00 each | 0% |
```

**Total observed spend (both periods combined): ≈ $0.4535 USD**

Note: This is not a "monthly" figure in the strict sense — the two periods cover ~30 days total (7 days actual + 23 days estimated), so it approximates one month of spend at current usage levels.

---

## Top 5 Recommended Actions

*Ranked by severity/risk since no material savings could be estimated (total spend is near-zero):*

1. **Investigate "EC2 - Other" charges** — confirm no forgotten NAT Gateway, VPC endpoint, or snapshot exists outside the resources captured by this scan (`aws ec2 describe-nat-gateways`, `describe-vpc-endpoints`, `describe-snapshots`).
2. **Add lifecycle policy to `ekadantha-embroidery-upload`** — highest priority of the two buckets since "upload" buckets often accumulate transient files that should expire.
3. **Add lifecycle policy to `ekadantha-embroidery-designs`** — apply Standard-IA/Glacier transition if designs are accessed infrequently after initial upload.
4. **Confirm ECR repository has a lifecycle policy** for untagged/old images, since ECR is currently the largest single cost driver (33% of spend) — not directly requested in scope but worth a quick check: `aws ecr describe-repositories --region ap-south-1` and `aws ecr get-lifecycle-policy --repository-name <repo> --region ap-south-1`.
5. **Re-run this audit periodically** as the account scales — right now there is no waste to eliminate, but the audit trail should be established before infrastructure grows.

---

## Final Notes

* **EC2 Instances, EBS Volumes, Elastic IPs, Load Balancers, RDS Instances**: No findings — all returned **empty result sets** in the provided data. There is currently no compute or database infrastructure provisioned in `ap-south-1` for this account, so no over-provisioning, idle-resource, or orphaned-resource findings apply to these categories.
* **Reserved Instances / Savings Plans**: Not applicable — no running EC2 or RDS instances exist to evaluate for RI/Savings Plan coverage.
* **Multi-AZ / storage type misconfiguration (RDS)**: Not applicable — no RDS instances found.
* **S3 Storage & Logging**: Two buckets found, both lacking visible lifecycle configuration (findings above). Object counts, total size, and access patterns were **not available** in the provided data — actual cost impact of adding lifecycle rules cannot be quantified without `s3api list-objects-v2` / S3 Storage Lens data.
* **Cost Explorer data limitation**: The two time periods provided are not a clean single 30-day window (one spans 7 days marked `"Estimated": false`, the other spans 23 days marked `"Estimated": true`). This report treats them as an approximate combined 30-day/monthly total, but a single continuous `get-cost-and-usage` call with explicit start/end dates is recommended for a more precise monthly figure.
* **ECR cost driver**: ECR is the single largest line item (~33% of total spend) yet no ECR repository data was provided in the input for review — this limits our ability to assess whether image lifecycle policies are configured. Recommend running `aws ecr describe-repositories --region ap-south-1` in a follow-up pass.
* **Overall conclusion**: Given the near-zero total spend (~$0.45 across the reviewed window) and absence of any provisioned compute/storage/database resources, this account shows **no significant cost waste** at this time. The findings above are precautionary/hygiene items rather than active cost leaks.