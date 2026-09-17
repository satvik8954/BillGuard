"""
BillGuard resource checks (tasks 3-4).

Pure scanning logic: given a session that's already inside the user's
account (via assume_role), find billable leftovers. No CLI code and no
hardcoded "platform" profile here, so this same module can be imported
by the local CLI (scanner_local.py) and, later, by the ScanAccount
Lambda (task 6) without changes.
"""

import boto3
from botocore.exceptions import ClientError

# Approximate prices (USD per hour), for resources with one flat rate
# regardless of size/type. Update as needed.
PRICES_USD_PER_HOUR = {
    "elastic_ip_unused": 0.005,
    "nat_gateway": 0.045,
    "eks_cluster": 0.10,
    "classic_load_balancer": 0.025,
    "application_load_balancer": 0.0225,
    "network_load_balancer": 0.0225,
}

# Approximate EC2 on-demand prices (USD per hour) by instance type.
# "_default" covers any type not listed here.
EC2_INSTANCE_PRICES_USD_PER_HOUR = {
    "t2.micro": 0.0116,
    "t2.small": 0.023,
    "t2.medium": 0.0464,
    "t3.micro": 0.0104,
    "t3.small": 0.0208,
    "t3.medium": 0.0416,
    "t3.large": 0.0832,
    "m5.large": 0.096,
    "m5.xlarge": 0.192,
    "c5.large": 0.085,
    "r5.large": 0.126,
    "_default": 0.10,
}

# Approximate EBS prices (USD per GB per month) by volume type.
EBS_VOLUME_PRICES_USD_PER_GB_MONTH = {
    "gp2": 0.10,
    "gp3": 0.08,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
    "_default": 0.10,
}

# Approximate RDS on-demand prices (USD per hour) by instance class.
RDS_INSTANCE_PRICES_USD_PER_HOUR = {
    "db.t3.micro": 0.017,
    "db.t3.small": 0.034,
    "db.t3.medium": 0.068,
    "db.m5.large": 0.171,
    "db.r5.large": 0.24,
    "_default": 0.20,
}

# Approximate OpenSearch prices (USD per hour) per data node instance.
OPENSEARCH_INSTANCE_PRICES_USD_PER_HOUR = {
    "t3.small.search": 0.036,
    "t3.medium.search": 0.073,
    "m5.large.search": 0.142,
    "_default": 0.15,
}

# Approximate SageMaker prices (USD per hour) per instance, shared by
# endpoints and notebook instances (both use "ml.*" instance types).
SAGEMAKER_INSTANCE_PRICES_USD_PER_HOUR = {
    "ml.t2.medium": 0.065,
    "ml.t3.medium": 0.065,
    "ml.m5.large": 0.115,
    "ml.m5.xlarge": 0.23,
    "_default": 0.20,
}

USD_TO_INR = 88.0  # approximate; adjust to the current rate


def assume_role(
    role_arn: str, external_id: str, caller_session: boto3.Session | None = None
) -> boto3.Session:
    """Borrow the user's role and return a session that acts inside their account.

    caller_session is the identity doing the borrowing — the platform's own
    identity. It defaults to boto3's normal credential lookup (a Lambda's
    execution role, in production) rather than a hardcoded profile, so this
    function works unchanged from a Lambda.
    """
    caller_session = caller_session or boto3.Session()
    creds = caller_session.client("sts").assume_role(
        RoleArn=role_arn,
        RoleSessionName="billguard-scan",
        ExternalId=external_id,
        DurationSeconds=900,
    )["Credentials"]
    return boto3.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    )


def daily_inr(price_key: str) -> float:
    return hourly_to_daily_inr(PRICES_USD_PER_HOUR[price_key])


def hourly_to_daily_inr(usd_per_hour: float) -> float:
    return round(usd_per_hour * 24 * USD_TO_INR, 2)


def gb_month_to_daily_inr(price_per_gb_month: float, size_gb: float) -> float:
    daily_usd = size_gb * price_per_gb_month / 30
    return round(daily_usd * USD_TO_INR, 2)


def check_unused_elastic_ips(session: boto3.Session, region: str) -> list[dict]:
    ec2 = session.client("ec2", region_name=region)
    findings = []
    for address in ec2.describe_addresses()["Addresses"]:
        if "AssociationId" not in address:
            findings.append({
                "type": "Unused Elastic IP",
                "region": region,
                "resourceId": address.get("AllocationId"),
                "name": address.get("PublicIp"),
                "estDailyCostInr": daily_inr("elastic_ip_unused"),
                "howToDelete": "EC2 console → Elastic IPs → select it → Actions → Release Elastic IP address",
            })
    return findings


def check_ec2_instances(session: boto3.Session, region: str) -> list[dict]:
    ec2 = session.client("ec2", region_name=region)
    findings = []
    paginator = ec2.get_paginator("describe_instances")
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                state = instance["State"]["Name"]
                if state not in ("running", "stopped"):
                    continue
                instance_type = instance["InstanceType"]
                name = next(
                    (t["Value"] for t in instance.get("Tags", []) if t["Key"] == "Name"),
                    instance["InstanceId"],
                )
                if state == "running":
                    usd_per_hour = EC2_INSTANCE_PRICES_USD_PER_HOUR.get(
                        instance_type, EC2_INSTANCE_PRICES_USD_PER_HOUR["_default"]
                    )
                    cost = hourly_to_daily_inr(usd_per_hour)
                    howto = "EC2 console → Instances → select it → Instance state → Terminate instance"
                else:
                    cost = 0.0
                    howto = (
                        "EC2 console → Instances → select it → Instance state → Terminate instance "
                        "(stopped, but its attached EBS volumes keep billing)"
                    )
                findings.append({
                    "type": f"EC2 instance ({state})",
                    "region": region,
                    "resourceId": instance["InstanceId"],
                    "name": f"{name} ({instance_type})",
                    "estDailyCostInr": cost,
                    "howToDelete": howto,
                })
    return findings


def check_unattached_ebs_volumes(session: boto3.Session, region: str) -> list[dict]:
    ec2 = session.client("ec2", region_name=region)
    findings = []
    paginator = ec2.get_paginator("describe_volumes")
    for page in paginator.paginate(Filters=[{"Name": "status", "Values": ["available"]}]):
        for volume in page["Volumes"]:
            volume_type = volume["VolumeType"]
            size_gb = volume["Size"]
            price_per_gb_month = EBS_VOLUME_PRICES_USD_PER_GB_MONTH.get(
                volume_type, EBS_VOLUME_PRICES_USD_PER_GB_MONTH["_default"]
            )
            findings.append({
                "type": "Unattached EBS volume",
                "region": region,
                "resourceId": volume["VolumeId"],
                "name": f"{size_gb} GiB {volume_type}",
                "estDailyCostInr": gb_month_to_daily_inr(price_per_gb_month, size_gb),
                "howToDelete": "EC2 console → Volumes → select it → Actions → Delete volume",
            })
    return findings


def check_nat_gateways(session: boto3.Session, region: str) -> list[dict]:
    ec2 = session.client("ec2", region_name=region)
    findings = []
    paginator = ec2.get_paginator("describe_nat_gateways")
    for page in paginator.paginate(Filter=[{"Name": "state", "Values": ["available"]}]):
        for gateway in page["NatGateways"]:
            findings.append({
                "type": "NAT Gateway",
                "region": region,
                "resourceId": gateway["NatGatewayId"],
                "name": gateway["NatGatewayId"],
                "estDailyCostInr": daily_inr("nat_gateway"),
                "howToDelete": "VPC console → NAT Gateways → select it → Actions → Delete NAT gateway",
            })
    return findings


def check_load_balancers(session: boto3.Session, region: str) -> list[dict]:
    findings = []

    elbv2 = session.client("elbv2", region_name=region)
    paginator = elbv2.get_paginator("describe_load_balancers")
    for page in paginator.paginate():
        for lb in page["LoadBalancers"]:
            lb_type = lb["Type"]  # "application" or "network"
            price_key = (
                "application_load_balancer" if lb_type == "application" else "network_load_balancer"
            )
            findings.append({
                "type": f"{lb_type.title()} Load Balancer",
                "region": region,
                "resourceId": lb["LoadBalancerArn"],
                "name": lb["LoadBalancerName"],
                "estDailyCostInr": daily_inr(price_key),
                "howToDelete": "EC2 console → Load Balancers → select it → Actions → Delete",
            })

    elb = session.client("elb", region_name=region)
    paginator = elb.get_paginator("describe_load_balancers")
    for page in paginator.paginate():
        for lb in page["LoadBalancerDescriptions"]:
            findings.append({
                "type": "Classic Load Balancer",
                "region": region,
                "resourceId": lb["LoadBalancerName"],
                "name": lb["LoadBalancerName"],
                "estDailyCostInr": daily_inr("classic_load_balancer"),
                "howToDelete": "EC2 console → Load Balancers (Classic) → select it → Actions → Delete",
            })

    return findings


def check_rds_instances(session: boto3.Session, region: str) -> list[dict]:
    rds = session.client("rds", region_name=region)
    findings = []
    paginator = rds.get_paginator("describe_db_instances")
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            instance_class = db["DBInstanceClass"]
            usd_per_hour = RDS_INSTANCE_PRICES_USD_PER_HOUR.get(
                instance_class, RDS_INSTANCE_PRICES_USD_PER_HOUR["_default"]
            )
            findings.append({
                "type": "RDS database instance",
                "region": region,
                "resourceId": db["DBInstanceIdentifier"],
                "name": f"{db['DBInstanceIdentifier']} ({instance_class})",
                "estDailyCostInr": hourly_to_daily_inr(usd_per_hour),
                "howToDelete": "RDS console → Databases → select it → Actions → Delete",
            })
    return findings


def check_opensearch_domains(session: boto3.Session, region: str) -> list[dict]:
    es = session.client("es", region_name=region)
    findings = []
    domain_names = [d["DomainName"] for d in es.list_domain_names()["DomainNames"]]
    if not domain_names:
        return findings
    for status in es.describe_domains(DomainNames=domain_names)["DomainStatusList"]:
        cluster_config = status["ClusterConfig"]
        instance_type = cluster_config["InstanceType"]
        instance_count = cluster_config["InstanceCount"]
        usd_per_hour = OPENSEARCH_INSTANCE_PRICES_USD_PER_HOUR.get(
            instance_type, OPENSEARCH_INSTANCE_PRICES_USD_PER_HOUR["_default"]
        )
        findings.append({
            "type": "OpenSearch domain",
            "region": region,
            "resourceId": status["DomainName"],
            "name": f"{status['DomainName']} ({instance_count}x {instance_type})",
            "estDailyCostInr": hourly_to_daily_inr(usd_per_hour * instance_count),
            "howToDelete": "OpenSearch Service console → Domains → select it → Delete",
        })
    return findings


def check_sagemaker_endpoints(session: boto3.Session, region: str) -> list[dict]:
    sm = session.client("sagemaker", region_name=region)
    findings = []
    paginator = sm.get_paginator("list_endpoints")
    for page in paginator.paginate():
        for endpoint in page["Endpoints"]:
            findings.append({
                "type": "SageMaker endpoint",
                "region": region,
                "resourceId": endpoint["EndpointName"],
                "name": endpoint["EndpointName"],
                "estDailyCostInr": hourly_to_daily_inr(SAGEMAKER_INSTANCE_PRICES_USD_PER_HOUR["_default"]),
                "howToDelete": "SageMaker console → Inference → Endpoints → select it → Delete",
            })
    return findings


def check_sagemaker_notebook_instances(session: boto3.Session, region: str) -> list[dict]:
    sm = session.client("sagemaker", region_name=region)
    findings = []
    paginator = sm.get_paginator("list_notebook_instances")
    for page in paginator.paginate():
        for notebook in page["NotebookInstances"]:
            status = notebook["NotebookInstanceStatus"]
            if status not in ("InService", "Stopped"):
                continue
            instance_type = notebook["InstanceType"]
            usd_per_hour = SAGEMAKER_INSTANCE_PRICES_USD_PER_HOUR.get(
                instance_type, SAGEMAKER_INSTANCE_PRICES_USD_PER_HOUR["_default"]
            )
            cost = hourly_to_daily_inr(usd_per_hour) if status == "InService" else 0.0
            findings.append({
                "type": f"SageMaker notebook instance ({status})",
                "region": region,
                "resourceId": notebook["NotebookInstanceName"],
                "name": f"{notebook['NotebookInstanceName']} ({instance_type})",
                "estDailyCostInr": cost,
                "howToDelete": "SageMaker console → Notebook instances → select it → Actions → Delete",
            })
    return findings


def check_eks_clusters(session: boto3.Session, region: str) -> list[dict]:
    eks = session.client("eks", region_name=region)
    findings = []
    paginator = eks.get_paginator("list_clusters")
    for page in paginator.paginate():
        for cluster_name in page["clusters"]:
            findings.append({
                "type": "EKS cluster",
                "region": region,
                "resourceId": cluster_name,
                "name": cluster_name,
                "estDailyCostInr": daily_inr("eks_cluster"),
                "howToDelete": "EKS console → Clusters → select it → Delete (delete node groups first if any)",
            })
    return findings


CHECKS = [
    check_unused_elastic_ips,
    check_ec2_instances,
    check_unattached_ebs_volumes,
    check_nat_gateways,
    check_load_balancers,
    check_rds_instances,
    check_opensearch_domains,
    check_sagemaker_endpoints,
    check_sagemaker_notebook_instances,
    check_eks_clusters,
]


def scan(session: boto3.Session, regions: list[str]) -> dict:
    findings, skipped = [], []
    for region in regions:
        for check in CHECKS:
            try:
                findings.extend(check(session, region))
            except ClientError as err:
                # One failing region or service must not stop the whole scan.
                skipped.append({
                    "region": region,
                    "check": check.__name__,
                    "error": err.response["Error"]["Code"],
                })
    return {"findings": findings, "skipped": skipped}
