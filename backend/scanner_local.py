"""
BillGuard local scanner CLI (tasks 3-4).

Thin command-line wrapper: the actual checks live in backend/scanner/checks.py
so the same code can run from a Lambda later (task 6) without changes.

Usage (Windows cmd, venv active):
  python backend\\scanner_local.py --role-arn arn:aws:iam::312057051737:role/BillGuardReadOnly --external-id test-456 --regions ap-south-1
"""

import argparse
import json

import boto3

from scanner.checks import assume_role, scan

PLATFORM_PROFILE = "platform"


def main() -> None:
    parser = argparse.ArgumentParser(description="BillGuard local scanner")
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--regions", nargs="+", default=["ap-south-1"])
    args = parser.parse_args()

    caller_session = boto3.Session(profile_name=PLATFORM_PROFILE)
    session = assume_role(args.role_arn, args.external_id, caller_session)
    result = scan(session, args.regions)

    total = sum(f["estDailyCostInr"] for f in result["findings"])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nFound {len(result['findings'])} forgotten resource(s), about ₹{total:.2f}/day.")


if __name__ == "__main__":
    main()
