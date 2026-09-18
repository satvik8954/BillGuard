"""
POST /connect/init — Lambda handler (task 5, wired up for real in task 6).

Generates an ExternalId for the signed-in user, saves a "pending" profile
row, and returns a CloudFormation quick-create URL that creates their
read-only role (user-role/billguard-role.yaml) with that ExternalId
pre-filled.

Idempotent by design: the role name is fixed (BillGuardReadOnly) and its
trust policy's sts:ExternalId condition is baked in at stack-create time.
If a caller invokes init twice while a stack is mid-flight (a reload, a
second click on "Open CloudFormation", etc.) before generating a new
ExternalId would silently invalidate the role they already deployed, since
the already-created role's trust policy still references the old value.
So: reuse the existing externalId whenever the profile is still "pending".
Only mint a fresh one when there's no profile yet, or the user is
deliberately reconnecting ("connected" or "error").

ROLE_TEMPLATE_URL and SCANNER_ROLE_ARN come from real infrastructure now:
the public S3 bucket holding billguard-role.yaml, and the ScannerFunction's
own execution role (the only identity CLAUDE.md's hard rules allow the
user's role to trust) — see template.yaml.
"""

import json
import os
import uuid
from urllib.parse import quote

import boto3
from botocore.config import Config

TABLE_NAME = os.environ["TABLE_NAME"]
ROLE_TEMPLATE_URL = os.environ["ROLE_TEMPLATE_URL"]
SCANNER_ROLE_ARN = os.environ["SCANNER_ROLE_ARN"]

# Fail fast on a slow/unreachable AWS endpoint instead of sitting until the
# Lambda's own Timeout kills the invocation.
BOTO_CONFIG = Config(connect_timeout=5, read_timeout=10)

table = boto3.resource("dynamodb", config=BOTO_CONFIG).Table(TABLE_NAME)


def handler(event, context):
    user_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]

    existing_profile = table.get_item(Key={"PK": f"USER#{user_sub}", "SK": "PROFILE"}).get("Item")

    if existing_profile and existing_profile.get("status") == "pending" and "externalId" in existing_profile:
        external_id = existing_profile["externalId"]
    else:
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
        f"?templateURL={quote(ROLE_TEMPLATE_URL, safe='')}"
        "&stackName=BillGuard"
        f"&param_ExternalId={external_id}"
        f"&param_TrustedPrincipalArn={quote(SCANNER_ROLE_ARN, safe='')}"
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({
            "externalId": external_id,
            "quickCreateUrl": quick_create_url,
        }),
    }
