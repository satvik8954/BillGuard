"""
GET /connect/status — Lambda handler.

Tells the frontend whether the signed-in user has already connected an AWS
account, so returning users go straight to the dashboard instead of being
asked to create the role again. Reads the PROFILE row only; never returns
the ExternalId.

status: "none" (never started), "pending" (init called, verify not done),
"connected", or "error".
"""

import json
import os

import boto3
from botocore.config import Config

TABLE_NAME = os.environ["TABLE_NAME"]

# Fail fast on a slow/unreachable AWS endpoint instead of sitting until the
# Lambda's own Timeout kills the invocation.
BOTO_CONFIG = Config(connect_timeout=5, read_timeout=10)

table = boto3.resource("dynamodb", config=BOTO_CONFIG).Table(TABLE_NAME)


def handler(event, context):
    user_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]

    profile = table.get_item(Key={"PK": f"USER#{user_sub}", "SK": "PROFILE"}).get("Item", {})

    body = {"status": profile.get("status", "none")}
    if profile.get("awsAccountId"):
        body["awsAccountId"] = profile["awsAccountId"]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }
