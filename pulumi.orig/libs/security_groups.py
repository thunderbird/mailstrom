import pulumi
import pulumi_aws as aws

name_prefix = pulumi.get_project() + "-" + pulumi.get_stack()

def create_mail_sec_group(vpc_id):
    sec_group = aws.ec2.SecurityGroup(f"{name_prefix}-mailsec",
        vpc_id=vpc_id,
        ingress=[
            {"protocol": "tcp", "from_port": 443, "to_port": 443, "cidr_blocks": ["0.0.0.0/0"]}, # HTTPS Web Admin
            {"protocol": "tcp", "from_port": 587, "to_port": 587, "cidr_blocks": ["0.0.0.0/0"]},
            {"protocol": "tcp", "from_port": 465, "to_port": 465, "cidr_blocks": ["0.0.0.0/0"]},
            {"protocol": "tcp", "from_port": 143, "to_port": 143, "cidr_blocks": ["0.0.0.0/0"]},
            {"protocol": "tcp", "from_port": 993, "to_port": 993, "cidr_blocks": ["0.0.0.0/0"]},
            {"protocol": "tcp", "from_port": 4190, "to_port": 4190, "cidr_blocks": ["0.0.0.0/0"]},
            {"protocol": "tcp", "from_port": 25, "to_port": 25, "cidr_blocks": ["0.0.0.0/0"]},
        ],
        egress=[{"protocol": "-1", "from_port": 0, "to_port": 0, "cidr_blocks": ["0.0.0.0/0"]}]
    )
    return sec_group


def create_config_sec_group(vpc_id):
    security_group = aws.ec2.SecurityGroup(f"{name_prefix}-adminconfigsec",
        vpc_id=vpc_id,
        ingress=[
            {"protocol": "tcp", "from_port": 8080, "to_port": 8080, "cidr_blocks": ["207.216.109.73/32"]}, # No HTTPS
            {"protocol": "tcp", "from_port": 22, "to_port": 22, "cidr_blocks": ["207.216.109.73/32"]},
        ]
    )
    return security_group
