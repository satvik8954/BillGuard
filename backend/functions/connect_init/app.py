"""
POST /connect/init — Lambda handler (task 5).

Generates a fresh ExternalId for the signed-in user, saves a "pending"
profile row, and returns a CloudFormation quick-create URL that creates
their read-only role (user-role/billguard-role.yaml) with that ExternalId
pre-filled.
"""

import json
import os
import uuid

import boto3

TABLE_NAME = os.environ["TABLE_NAME"]

# Placeholders until later tasks fill in the real values:
#  - ROLE_TEMPLATE_URL: where user-role/billguard-role.yaml is hosted (task 5b/8, an S3 URL).
#  - SCANNER_ROLE_ARN: the ScanAccount Lambda's own role ARN (task 6). Per CLAUDE.md's
#    hard rules, this must be a specific role ARN, never the whole platform account.
ROLE_TEMPLATE_URL = os.environ.get("ROLE_TEMPLATE_URL", "REPLACE_ME_ROLE_TEMPLATE_URL")
SCANNER_ROLE_ARN = os.environ.get("SCANNER_ROLE_ARN", "REPLACE_ME_SCANNER_ROLE_ARN")

table = boto3.resource("dynamodb").Table(TABLE_NAME)


def handler(event, context):
    user_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    external_id = str(uuid.uuid4())

    table.put_item(Item={
        "PK": f"USER#{user_sub}",
        "SK": "PROFILE",
        "externalId": external_id,
        "status": "pending",
    })

    quick_create_url = (
        "https://console.aws.amazon.com/cloudformation/home"
        "?region=ap-south-1#/stacks/quickcreate"
        f"?templateURL={ROLE_TEMPLATE_URL}"
        "&stackName=BillGuard"
        f"&param_ExternalId={external_id}"
        f"&param_TrustedPrincipalArn={SCANNER_ROLE_ARN}"
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "externalId": external_id,
            "quickCreateUrl": quick_create_url,
        }),
    }
