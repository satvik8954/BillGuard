"""
Step Functions task: SaveFindings — the last step of ScanAccount (task 6).

Flattens every region's results from the Map state, diffs them against
what's already in DynamoDB (still-found resources stay/become "active";
anything previously active but missing this time is "resolved"), and
records one SCAN# summary row plus the profile's lastScanAt.
"""

import os
from datetime import datetime, timezone
from decimal import Decimal

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config

TABLE_NAME = os.environ["TABLE_NAME"]

# Fail fast on a slow/unreachable AWS endpoint instead of sitting until the
# Lambda's own Timeout kills the invocation.
BOTO_CONFIG = Config(connect_timeout=5, read_timeout=10)

table = boto3.resource("dynamodb", config=BOTO_CONFIG).Table(TABLE_NAME)


def handler(event, context):
    user_sub = event["userSub"]
    scan_results = event.get("scanResults", [])
    now = datetime.now(timezone.utc).isoformat()

    regions_scanned, regions_skipped, findings = [], [], []
    for region_result in scan_results:
        regions_scanned.append(region_result["region"])
        regions_skipped.extend(region_result.get("skipped", []))
        findings.extend(region_result.get("findings", []))

    existing_items = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{user_sub}") & Key("SK").begins_with("FINDING#")
    )["Items"]
    existing_by_sk = {item["SK"]: item for item in existing_items}

    seen_sks = set()
    for finding in findings:
        sk = f"FINDING#{finding['region']}#{finding['resourceId']}"
        seen_sks.add(sk)
        first_seen = existing_by_sk.get(sk, {}).get("firstSeen", now)
        table.put_item(Item={
            "PK": f"USER#{user_sub}",
            "SK": sk,
            "type": finding["type"],
            "name": finding["name"],
            "region": finding["region"],
            "resourceId": finding["resourceId"],
            # DynamoDB has no float type. Decimal(str(x)) avoids the binary
            # rounding you'd get from Decimal(x) directly on a float.
            "estDailyCostInr": Decimal(str(finding["estDailyCostInr"])),
            "howToDelete": finding["howToDelete"],
            "firstSeen": first_seen,
            "lastSeen": now,
            "status": "active",
        })

    for sk, item in existing_by_sk.items():
        if sk not in seen_sks and item.get("status") == "active":
            table.update_item(
                Key={"PK": item["PK"], "SK": sk},
                UpdateExpression="SET #status = :resolved",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":resolved": "resolved"},
            )

    table.put_item(Item={
        "PK": f"USER#{user_sub}",
        "SK": f"SCAN#{now}",
        "regionsScanned": regions_scanned,
        "regionsSkipped": regions_skipped,
        "findingsCount": len(findings),
    })

    table.update_item(
        Key={"PK": f"USER#{user_sub}", "SK": "PROFILE"},
        UpdateExpression="SET lastScanAt = :t",
        ExpressionAttributeValues={":t": now},
    )

    return {
        "userSub": user_sub,
        "regionsScanned": regions_scanned,
        "regionsSkipped": regions_skipped,
        "findingsCount": len(findings),
    }
