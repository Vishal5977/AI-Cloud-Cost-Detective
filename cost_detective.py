"""
AI Cloud Cost Detective - Claude version (AWS, scoped down).

Scans an AWS region using the AWS CLI (read-only), sends the real resource
and cost data to Claude for analysis, and saves a Markdown cost-optimization
report.

Prerequisites:
    - AWS CLI installed and configured with a READ-ONLY IAM user
      (aws configure --profile your-readonly-profile)
    - ANTHROPIC_API_KEY set as an environment variable

Usage:
    set ANTHROPIC_API_KEY=your_key_here      (Windows)
    export ANTHROPIC_API_KEY=your_key_here   (Mac/Linux)

    python cost_detective.py --region ap-south-1
    python cost_detective.py --region ap-south-1 --profile your-readonly-profile
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta

from anthropic import Anthropic

PROMPT_FILE = "prompt.md"
OUTPUT_DIR = "cost_reports"
MODEL = "claude-sonnet-5"

# Use aws.exe next to this script if present (Windows, no PATH setup needed),
# otherwise fall back to "aws" on PATH.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_AWS = os.path.join(SCRIPT_DIR, "aws.exe")
AWS_BIN = LOCAL_AWS if os.path.exists(LOCAL_AWS) else "aws"


def run_aws(args_list, profile=None, timeout=60):
    cmd = [AWS_BIN] + args_list
    if profile:
        cmd += ["--profile", profile]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return result.stdout.strip() or "(no output / empty result)"
        return f"[ERROR running 'aws {' '.join(args_list)}']\n{result.stderr.strip()}"
    except FileNotFoundError:
        return f"[SKIPPED] AWS CLI not found at '{AWS_BIN}'."
    except Exception as e:
        return f"[FAILED to run 'aws {' '.join(args_list)}']\n{e}"


def gather_aws_data(region: str, profile: str) -> str:
    today = datetime.utcnow().date()
    start = today - timedelta(days=30)

    commands = [
        ("Account Identity", ["sts", "get-caller-identity"]),
        ("EC2 Instances", ["ec2", "describe-instances", "--region", region]),
        ("EBS Volumes", ["ec2", "describe-volumes", "--region", region]),
        ("Elastic IPs", ["ec2", "describe-addresses", "--region", region]),
        ("Load Balancers", ["elbv2", "describe-load-balancers", "--region", region]),
        ("RDS Instances", ["rds", "describe-db-instances", "--region", region]),
        ("S3 Buckets", ["s3api", "list-buckets"]),
        (
            "Cost Explorer (last 30 days by service)",
            [
                "ce", "get-cost-and-usage",
                "--time-period", f"Start={start},End={today}",
                "--granularity", "MONTHLY",
                "--metrics", "UnblendedCost",
                "--group-by", "Type=DIMENSION,Key=SERVICE",
            ],
        ),
    ]

    sections = []
    for label, args_list in commands:
        print(f"Running: aws {' '.join(args_list)}")
        output = run_aws(args_list, profile=profile)
        sections.append(f"### {label}\n```\n{output}\n```")

    return "\n\n".join(sections)


def build_prompt(region: str, profile: str) -> str:
    if not os.path.exists(PROMPT_FILE):
        print(f"ERROR: {PROMPT_FILE} not found in current directory.")
        sys.exit(1)

    with open(PROMPT_FILE, "r", encoding="utf-8") as f:
        template = f.read()

    template = template.replace("<REGION>", region)
    aws_data = gather_aws_data(region, profile)

    return (
        f"{template}\n\n"
        f"---\n\n"
        f"# Actual AWS Data (collected via AWS CLI, read-only)\n\n"
        f"{aws_data}"
    )


def main():
    parser = argparse.ArgumentParser(description="AI Cloud Cost Detective (AWS + Claude)")
    parser.add_argument("--region", default="ap-south-1", help="AWS region to scan (default: ap-south-1)")
    parser.add_argument("--profile", default=None, help="AWS CLI profile to use (your read-only IAM user)")
    args = parser.parse_args()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    client = Anthropic(api_key=api_key)
    full_prompt = build_prompt(args.region, args.profile)

    print("\nSending cost analysis request to Claude...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": full_prompt}],
    )

    result_text = "".join(
        block.text for block in response.content if block.type == "text"
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(
        OUTPUT_DIR, f"cost_report_{args.region}_{timestamp}.md"
    )

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result_text)

    print(f"\nReport saved to: {output_file}\n")
    print("=" * 60)
    print(result_text)


if __name__ == "__main__":
    main()
