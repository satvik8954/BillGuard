"""
GET /findings — Lambda handler (task 6).

Reads real FINDING# rows for the signed-in user from DynamoDB, now that
ScanAccount (task 6) actually writes them. Replaces the fake data from
task 5.
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

    response = table.query(
        KeyConditionExpression=Key("PK").eq(f"USER#{user_sub}") & Key("SK").begins_with("FINDING#")
    )

    findings = [
        {
            "type": item["type"],
            "region": item["region"],
            "resourceId": item["resourceId"],
            "name": item["name"],
            # DynamoDB gives back Decimal, not float; json.dumps can't
            # serialize Decimal on its own.
            "estDailyCostInr": float(item["estDailyCostInr"]),
            "howToDelete": item["howToDelete"],
            "firstSeen": item["firstSeen"],
            "lastSeen": item["lastSeen"],
            "status": item["status"],
        }
        for item in response["Items"]
    ]

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"findings": findings}),
    }
