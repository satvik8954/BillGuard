"""
POST /connect/verify — Lambda handler (task 6, fixed for single-trusted-identity).

Body: { "roleArn": "..." }. Asks ScannerFunction to test AssumeRole against
the stored ExternalId (this function never calls sts:AssumeRole itself —
see LEARNING.md's "single trusted identity" section for why), reads the
account ID out of the role's own ARN, marks the profile "connected", and
starts the first ScanAccount execution.
"""

import json
import os

import boto3
from botocore.config import Config

TABLE_NAME = os.environ["TABLE_NAME"]
STATE_MACHINE_ARN = os.environ["SCAN_ACCOUNT_STATE_MACHINE_ARN"]
SCANNER_FUNCTION_ARN = os.environ["SCANNER_FUNCTION_ARN"]

# Fail fast on a slow/unreachable AWS endpoint instead of sitting until the
# Lambda's own Timeout kills the invocation.
BOTO_CONFIG = Config(connect_timeout=5, read_timeout=10)

table = boto3.resource("dynamodb", config=BOTO_CONFIG).Table(TABLE_NAME)
sfn = boto3.client("stepfunctions", config=BOTO_CONFIG)
lambda_client = boto3.client("lambda", config=BOTO_CONFIG)


def handler(event, context):
    user_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    body = json.loads(event.get("body") or "{}")
    role_arn = body.get("roleArn")

    if not role_arn:
        return _error(400, "roleArn is required")

    profile = table.get_item(Key={"PK": f"USER#{user_sub}", "SK": "PROFILE"}).get("Item")
    if not profile or "externalId" not in profile:
        return _error(400, "Call /connect/init first")

    external_id = profile["externalId"]
    account_id = role_arn.split(":")[4]

    invoke_response = lambda_client.invoke(
        FunctionName=SCANNER_FUNCTION_ARN,
        InvocationType="RequestResponse",
        Payload=json.dumps({"mode": "verify", "roleArn": role_arn, "externalId": external_id}).encode("utf-8"),
    )
    verify_result = json.loads(invoke_response["Payload"].read())

    if invoke_response.get("FunctionError") or not verify_result.get("ok"):
        error_code = verify_result.get("error", "Unknown")
        return _error(403, f"Could not assume role: {error_code}")

    table.update_item(
        Key={"PK": f"USER#{user_sub}", "SK": "PROFILE"},
        UpdateExpression="SET roleArn = :r, awsAccountId = :a, #status = :connected",
        ExpressionAttributeNames={"#status": "status"},
        ExpressionAttributeValues={":r": role_arn, ":a": account_id, ":connected": "connected"},
    )

    sfn.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        input=json.dumps({"userSub": user_sub, "roleArn": role_arn, "externalId": external_id}),
    )

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "connected", "awsAccountId": account_id}),
    }


def _error(status_code, message):
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
