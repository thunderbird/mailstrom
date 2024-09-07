import pulumi
import pulumi_aws as aws

name_prefix = pulumi.get_project() + "-" + pulumi.get_stack()

def create_iam_role_and_policy(s3_bucket_name):
    role = aws.iam.Role(f"{name_prefix}-mailserver-role", assume_role_policy="""
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    }
    """)

    policy = aws.iam.RolePolicy(f"{name_prefix}-mailserver-policy",
        role=role.id,
        policy=f"""
        {{
            "Version": "2012-10-17",
            "Statement": [
                {{
                    "Action": "s3:*",
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::{s3_bucket_name}",
                        "arn:aws:s3:::{s3_bucket_name}/*"
                    ]
                }}
            ]
        }}
        """)

    instance_profile = aws.iam.InstanceProfile(f"{name_prefix}-mailserver-instance-policy", role=role.name)

    return instance_profile
