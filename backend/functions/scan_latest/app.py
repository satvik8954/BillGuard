"""
GET /scan/latest — Lambda handler.

Returns the most recent SCAN# summary row for the signed-in user, or
{"scan": null} if they've never been scanned.
"""

import json
import os

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config

TABLE_NAME = os.environ["TABLE_NAME"]

# Fail fast on a slow/unreachable AWS endpoint instead of sitting until the
# Lambda's own Timeout kills the invocation.
BOTO_CONFIG = Config(connect_timeout=5, read_timeout=10)

table = boto3.resource("dynamodb", config=BOTO_CONFIG).Table(TABLE_NAME)


def handler(event, context):
    user_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]

    # SK is "SCAN#<isoTimestamp>", so ISO-8601's lexicographic-equals-
    # chronological ordering means the newest scan sorts last; querying
    # backwards (ScanIndexForward=False) with Limit=1 gets it in one call.
    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{user_sub}") & Key("SK").begins_with("SCAN#"),
        ScanIndexForward=False,
        Limit=1,
    )
    items = response["Items"]

    if not items:
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"scan": None}),
        }

    item = items[0]
    scan = {
        "timestamp": item["SK"].split("SCAN#", 1)[1],
        "regionsScanned": item.get("regionsScanned", []),
        "regionsSkipped": item.get("regionsSkipped", []),
        "findingsCount": int(item.get("findingsCount", 0)),
    }
    if "monthToDateSpendUsd" in item:
        scan["monthToDateSpendUsd"] = float(item["monthToDateSpendUsd"])

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"scan": scan}),
    }
