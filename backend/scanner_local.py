"""
BillGuard local scanner (task 3).

Assumes the user's read-only role from the platform account and looks for
unused Elastic IPs. More checks get added to CHECKS in task 4.

Usage (Windows cmd, venv active):
  python backend\\scanner_local.py --role-arn arn:aws:iam::312057051737:role/BillGuardReadOnly --external-id test-456 --regions ap-south-1
"""

import argparse
import json

import boto3
from botocore.exceptions import ClientError

PLATFORM_PROFILE = "platform"

# Approximate prices (USD per hour). Update as needed.
PRICES_USD_PER_HOUR = {
    "elastic_ip_unused": 0.005,
}
USD_TO_INR = 88.0  # approximate; adjust to the current rate


def assume_role(role_arn: str, external_id: str) -> boto3.Session:
    """Borrow the user's role and return a session that acts inside their account."""
    platform = boto3.Session(profile_name=PLATFORM_PROFILE)
    creds = platform.client("sts").assume_role(
        RoleArn=role_arn,
        RoleSessionName="billguard-local-scan",
        ExternalId=external_id,
        DurationSeconds=900,
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def daily_inr(price_key: str) -> float:
    return round(PRICES_USD_PER_HOUR[price_key] * 24 * USD_TO_INR, 2)


def check_unused_elastic_ips(session: boto3.Session, region: str) -> list[dict]:
    ec2 = session.client("ec2", region_name=region)
    findings = []
    for address in ec2.describe_addresses()["Addresses"]:
        if "AssociationId" not in address:
            findings.append({
                "type": "Unused Elastic IP",
                "region": region,
                "resourceId": address.get("AllocationId"),
                "name": address.get("PublicIp"),
                "estDailyCostInr": daily_inr("elastic_ip_unused"),
                "howToDelete": "EC2 console → Elastic IPs → select it → Actions → Release Elastic IP address",
            })
    return findings


CHECKS = [
    check_unused_elastic_ips,
]


def scan(session: boto3.Session, regions: list[str]) -> dict:
    findings, skipped = [], []
    for region in regions:
        for check in CHECKS:
            try:
                findings.extend(check(session, region))
            except ClientError as err:
                # One failing region or service must not stop the whole scan.
                skipped.append({
                    "region": region,
                    "check": check.__name__,
                    "error": err.response["Error"]["Code"],
                })
    return {"findings": findings, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description="BillGuard local scanner")
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--external-id", required=True)
    parser.add_argument("--regions", nargs="+", default=["ap-south-1"])
    args = parser.parse_args()

    session = assume_role(args.role_arn, args.external_id)
    result = scan(session, args.regions)

    total = sum(f["estDailyCostInr"] for f in result["findings"])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nFound {len(result['findings'])} forgotten resource(s), about ₹{total:.2f}/day.")


if __name__ == "__main__":
    main()
