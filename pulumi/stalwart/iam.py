"""
Small module to build Stalwart IAM resources.
"""

import json
import pulumi_aws as aws

from tb_pulumi.constants import ASSUME_ROLE_POLICY


def iam(
    self,
    log_group_arn: str,
    s3_policy: aws.iam.Policy,
) -> tuple[
    aws.iam.Policy, aws.iam.Role, aws.iam.RolePolicyAttachment, aws.iam.RolePolicyAttachment, aws.iam.InstanceProfile
]:
    """Build IAM resources needed by Stalwart.

    :param s3_policy: IAM policy granting access to Stalwart's S3 bucket.
    :type s3_policy: aws.iam.Policy

    :return: Series of IAM resources for Stalwart.
    :rtype: tuple[ tb_pulumi.iam.UserWithAccessKey, aws.iam.Policy, aws.iam.Role, aws.iam.RolePolicyAttachment,
        aws.iam.InstanceProfile ]
    """

    # Build a policy which will grant the nodes access to their own configuration data
    bootstrap_secret_arns = [
        (
            'arn:aws:secretsmanager:'
            + f'{self.project.aws_region}:{self.project.aws_account_id}'
            + f':secret:mailstrom/{self.project.stack}/stalwart.postboot.*'
        ),
    ]
    profile_postboot_policy_doc = {
        'Version': '2012-10-17',
        'Statement': [
            {
                'Sid': 'AllowPostbootSecretAccess',
                'Effect': 'Allow',
                'Action': ['secretsmanager:GetSecretValue'],
                'Resource': bootstrap_secret_arns,
            }
        ],
    }

    profile_policy = aws.iam.Policy(
        f'{self.name}-policy-nodeprofile',
        path='/',
        description='Policy for the Stalwart node instance profile',
        policy=json.dumps(profile_postboot_policy_doc),
    )
    arp = ASSUME_ROLE_POLICY.copy()
    arp['Statement'][0]['Principal']['Service'] = 'ec2.amazonaws.com'
    role = aws.iam.Role(
        f'{self.name}-role-nodeprofile',
        name=f'{self.name}-stalwart-node-profile',
        assume_role_policy=json.dumps(arp),
        path='/',
    )
    profile_postboot_attachment = aws.iam.RolePolicyAttachment(
        f'{self.name}-rpa-nodeprofile-postboot',
        role=role.name,
        policy_arn=profile_policy.arn,
    )
    profile_s3_attachment = aws.iam.RolePolicyAttachment(
        f'{self.name}-rpa-nodeprofile-s3',
        role=role.name,
        policy_arn=s3_policy.arn,
    )
    profile_logwrite_attachment = aws.iam.RolePolicyAttachment(
        f'{self.name}-rpa-nodeprofile-logs',
        role=role.name,
        policy_arn=log_group_arn,
    )

    profile = aws.iam.InstanceProfile(f'{self.name}-ip-nodeprofile', name=f'{self.name}-nodeprofile', role=role.name)

    return (
        profile_policy,
        role,
        profile_postboot_attachment,
        profile_s3_attachment,
        profile_logwrite_attachment,
        profile,
    )
