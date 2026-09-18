"""
POST /scan — Lambda handler.

Starts a fresh ScanAccount execution for the signed-in user, using their
stored roleArn/externalId (never accepted from the request — always the
values verified back in /connect/verify). Refuses if they're not connected
yet, or if they scanned manually within the last 10 minutes.
"""

import json
import os
from datetime import datetime, timedelta, timezone

import boto3
from botocore.config import Config

TABLE_NAME = os.environ["TABLE_NAME"]
STATE_MACHINE_ARN = os.environ["SCAN_ACCOUNT_STATE_MACHINE_ARN"]
RATE_LIMIT = timedelta(minutes=10)

# Fail fast on a slow/unreachable AWS endpoint instead of sitting until the
# Lambda's own Timeout kills the invocation.
BOTO_CONFIG = Config(connect_timeout=5, read_timeout=10)

table = boto3.resource("dynamodb", config=BOTO_CONFIG).Table(TABLE_NAME)
sfn = boto3.client("stepfunctions", config=BOTO_CONFIG)


def handler(event, context):
    user_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]

    profile = table.get_item(Key={"PK": f"USER#{user_sub}", "SK": "PROFILE"}).get("Item")
    if not profile or profile.get("status") != "connected":
        return _error(409, "Account is not connected yet")

    now = datetime.now(timezone.utc)
    last_manual_scan_at = profile.get("lastManualScanAt")
    if last_manual_scan_at:
        elapsed = now - datetime.fromisoformat(last_manual_scan_at)
        if elapsed < RATE_LIMIT:
            wait_seconds = int((RATE_LIMIT - elapsed).total_seconds())
            return _error(429, f"Scan already ran recently. Try again in {wait_seconds}s.")

    sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps({
            "userSub": user_sub,
            "roleArn": profile["roleArn"],
            "externalId": profile["externalId"],
        }),
    )

    table.update_item(
        Key={"PK": f"USER#{user_sub}", "SK": "PROFILE"},
        UpdateExpression="SET lastManualScanAt = :t",
        ExpressionAttributeValues={":t": now.isoformat()},
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "started"}),
    }


def _error(status_code, message):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
