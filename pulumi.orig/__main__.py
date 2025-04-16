"""Stalwart mail server setup."""

import pulumi
import pulumi_aws as aws
import libs.security_groups as sec

from libs.cf_dns import configure_dns
from libs.iam_policies import create_iam_role_and_policy
from pathlib import Path

def create_s3_bucket(bucket_name):
    # Create an S3 bucket
    bucket = aws.s3.Bucket(bucket_name,
        bucket=bucket_name,
        acl="private",  # Ensure the bucket is private by default
        tags={
            "Name": bucket_name,
        }
        # force_destroy=True Necessary to delete the bucket when destroying the stack.
    )

    # Block all public access
    bucket_public_access_block = aws.s3.BucketPublicAccessBlock(f"{bucket_name}-block-public-access",
        bucket=bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )

    return bucket


# Configuration
config = pulumi.Config()
name_prefix = pulumi.get_project() + "-" + pulumi.get_stack()
key_pair = config.require("key_pair")
# This elastic IP needs to be changed for different stacks/environments.
elastic_ip = aws.ec2.get_elastic_ip(id=config.require('eip_id'))

# Network
vpc = aws.ec2.Vpc(f"{name_prefix}-vpc", cidr_block="10.0.0.0/16", tags={"Name": f"{name_prefix}-vpc"})

subnet1 = aws.ec2.Subnet(f"{name_prefix}-subnet1",
    vpc_id=vpc.id, cidr_block="10.0.1.0/24", availability_zone="us-east-1a", tags={"Name": f"{name_prefix}-subnet1"}
)

subnet2 = aws.ec2.Subnet(f"{name_prefix}-subnet2",
    vpc_id=vpc.id, cidr_block="10.0.2.0/24", availability_zone="us-east-1b", tags={"Name": f"{name_prefix}-subnet2"}
)

igw = aws.ec2.InternetGateway(f"{name_prefix}-igw", vpc_id=vpc.id, tags={"Name": f"{name_prefix}-igw"})

# Routing Table
route_table = aws.ec2.RouteTable(
    f"{name_prefix}-rt",
    vpc_id=vpc.id,
    routes=[{
        "cidr_block": "0.0.0.0/0",
        "gateway_id": igw.id
    }],
    tags={"Name": f"{name_prefix}-rt"})

rt_assoc = aws.ec2.RouteTableAssociation(f"{name_prefix}-subnet1-rt",
    subnet_id=subnet1.id, route_table_id=route_table.id
)


# DNS
domain = config.require("domain")
zone_id = config.require("zone_id")

# Config file for Stalwart
config_toml_path = Path("stalwart.toml")  # Replace with the actual path to your config.toml file

# Create Security Groups
mail_sec_group = sec.create_mail_sec_group(vpc.id)
config_sec_group = sec.create_config_sec_group(vpc.id)

# Create IAM Role and Policy
instance_profile = create_iam_role_and_policy(name_prefix)

# Create S3 Bucket with public access blocked
s3_bucket = create_s3_bucket(name_prefix)

# Define the EC2 instance
ami = aws.ec2.get_ami(filters=[{
    "name": "name",
    "values": ["amzn2-ami-hvm-*-x86_64-gp2"],
}],
    most_recent=True,
    owners=["amazon"])

ec2_instance = aws.ec2.Instance(f"{name_prefix}-mailserver",
    instance_type="m7a.large",
    ami=ami.id,
    subnet_id=subnet1.id,
    vpc_security_group_ids=[mail_sec_group.id, config_sec_group.id],
    iam_instance_profile=instance_profile.name,
    key_name=key_pair,
    user_data=f"""#!/bin/bash
        yum update -y
        yum install -y docker
        systemctl start docker
        usermod -a -G docker ec2-user
        mkdir -p /opt/stalwart-mail/etc/
        sudo systemctl disable --now postfix
        echo '{config_toml_path.read_text().strip()}' > /opt/stalwart-mail/etc/config.toml
        docker run -d -v /opt/stalwart-mail:/opt/stalwart-mail:rw \
        -p 443:443 -p 8080:8080 -p 25:25 -p 587:587 -p 465:465 -p 143:143 -p 993:993 -p 4190:4190 -p 110:110 -p 995:995 --name mail-server \
        stalwartlabs/mail-server:latest
        rm /var/lib/cloud/instance/sem/config_scripts_user""", # This dumb hack should make this run on every restart.
    tags={
        "Name": f"{name_prefix}-mailserver",
    }
)

eip_association = aws.ec2.EipAssociation(f"{name_prefix}-eip-assoc",
    instance_id=ec2_instance.id,
    allocation_id=elastic_ip.id,
)


dns_records = configure_dns(domain, zone_id, elastic_ip.public_ip)

# Export the DNS name of the load balancer and S3 bucket name
pulumi.export("service_ip", elastic_ip.public_ip)
pulumi.export("s3_bucket_name", s3_bucket.id)
