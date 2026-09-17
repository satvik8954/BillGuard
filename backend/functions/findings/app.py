"""
GET /findings — Lambda handler (task 5).

Returns hardcoded fake findings for now, matching the real FINDING# shape
from CLAUDE.md, so Madhu can build the dashboard UI before the scan
pipeline (tasks 6-7) exists. Replace FAKE_FINDINGS with a real DynamoDB
query (Query on PK = USER#<sub>, SK begins_with FINDING#) once ScanAccount
is writing findings.
"""

import json

FAKE_FINDINGS = [
    {
        "type": "Unused Elastic IP",
        "region": "ap-south-1",
        "resourceId": "eipalloc-0123456789abcdef0",
        "name": "13.204.175.86",
        "estDailyCostInr": 10.56,
        "howToDelete": "EC2 console → Elastic IPs → select it → Actions → Release Elastic IP address",
        "firstSeen": "2026-09-17T09:00:00Z",
        "lastSeen": "2026-09-18T09:00:00Z",
        "status": "active",
    },
    {
        "type": "RDS database instance",
        "region": "ap-south-1",
        "resourceId": "billguard-test-db",
        "name": "billguard-test-db (db.t3.micro)",
        "estDailyCostInr": 32.0,
        "howToDelete": "RDS console → Databases → select it → Actions → Delete",
        "firstSeen": "2026-09-16T09:00:00Z",
        "lastSeen": "2026-09-18T09:00:00Z",
        "status": "active",
    },
    {
        "type": "NAT Gateway",
        "region": "us-east-1",
        "resourceId": "nat-0123456789abcdef0",
        "name": "nat-0123456789abcdef0",
        "estDailyCostInr": 95.04,
        "howToDelete": "VPC console → NAT Gateways → select it → Actions → Delete NAT gateway",
        "firstSeen": "2026-09-10T09:00:00Z",
        "lastSeen": "2026-09-15T09:00:00Z",
        "status": "resolved",
    },
]


def handler(event, context):
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"findings": FAKE_FINDINGS}),
    }
