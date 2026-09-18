"""
ScannerFunction — the ONE Lambda that ever calls sts:AssumeRole on a user's
BillGuardReadOnly role (task 6 fix).

user-role/billguard-role.yaml's trust policy names exactly one principal:
this function's own execution role (ScannerFunctionRole). Every caller that
needs to act inside a user's account — connect_verify testing a new
connection, and the ScanAccount state machine listing regions and scanning
each one — goes through this function instead of assuming the role itself,
by invoking it (Step Functions Task, or a direct lambda:InvokeFunction) with
a "mode" field:

  mode: "verify"       -> just try AssumeRole; report ok/not ok
  mode: "list_regions" -> AssumeRole, then ec2:DescribeRegions
  mode: "scan" (default) -> AssumeRole, then run every check for one region

Reuses the exact same checks as the local CLI scanner (scanner/checks.py)
so there's only one copy of the scanning logic.
"""

from botocore.exceptions import ClientError

from scanner.checks import BOTO_CONFIG, assume_role, scan


def handler(event, context):
    mode = event.get("mode", "scan")
    role_arn = event["roleArn"]
    external_id = event["externalId"]

    if mode == "verify":
        return _verify(role_arn, external_id)
    if mode == "list_regions":
        return _list_regions(role_arn, external_id)
    return _scan_region(role_arn, external_id, event["region"])


def _verify(role_arn: str, external_id: str) -> dict:
    try:
        assume_role(role_arn, external_id)
        return {"ok": True}
    except ClientError as err:
        return {"ok": False, "error": err.response["Error"]["Code"]}


def _list_regions(role_arn: str, external_id: str) -> list[str]:
    session = assume_role(role_arn, external_id)
    ec2 = session.client("ec2", region_name="ap-south-1", config=BOTO_CONFIG)
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]


def _scan_region(role_arn: str, external_id: str, region: str) -> dict:
    try:
        session = assume_role(role_arn, external_id)
        result = scan(session, [region])
        return {"region": region, "findings": result["findings"], "skipped": result["skipped"]}
    except ClientError as err:
        # A disabled region or an AccessDenied here must not fail the whole
        # scan (CLAUDE.md hard rule) — report this one region as skipped
        # instead of raising, so the Map state's other iterations continue.
        return {
            "region": region,
            "findings": [],
            "skipped": [{"region": region, "check": "assume_role", "error": err.response["Error"]["Code"]}],
        }
