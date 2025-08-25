"""
Small module to build Stalwart IAM resources.
"""

import json
import pulumi
import pulumi_aws as aws
import tb_pulumi.iam

from tb_pulumi.constants import ASSUME_ROLE_POLICY, IAM_POLICY_DOCUMENT


def iam(
    self, s3_policy
) -> tuple[
    tb_pulumi.iam.UserWithAccessKey, aws.iam.Policy, aws.iam.Role, aws.iam.RolePolicyAttachment, aws.iam.InstanceProfile
]:
    """Build IAM resources needed by Stalwart.

    :param s3_policy: IAM policy granting access to Stalwart's S3 bucket.
    :type s3_policy: aws.iam.Policy

    :return: Series of IAM resources for Stalwart.
    :rtype: tuple[ tb_pulumi.iam.UserWithAccessKey, aws.iam.Policy, aws.iam.Role, aws.iam.RolePolicyAttachment,
        aws.iam.InstanceProfile ]
    """    

    iam_user_name = f'{self.project.name_prefix}-stalwart'
    iam_user = tb_pulumi.iam.UserWithAccessKey(
        name=f'{self.name}-user',
        project=self.project,
        exclude_from_project=True,
        user_name=iam_user_name,
        policies=[s3_policy],
        opts=pulumi.ResourceOptions(parent=self, depends_on=[s3_policy]),
    )

    # Build a policy which will grant the nodes access to their own configuration data
    bootstrap_secret_arns = [
        (
            'arn:aws:secretsmanager:'
            + f'{self.project.aws_region}:{self.project.aws_account_id}'
            + f':secret:mailstrom/{self.project.stack}/stalwart.postboot.*'
        ),
        (
            'arn:aws:secretsmanager:'
            + f'{self.project.aws_region}:{self.project.aws_account_id}'
            + f':secret:mailstrom/{self.project.stack}/iam.user.{iam_user_name}.access_key*'
        ),
    ]
    profile_policy_doc = IAM_POLICY_DOCUMENT.copy()
    profile_policy_doc['Statement'][0].update(
        {
            'Sid': 'AllowPostbootSecretAccess',
            'Action': ['secretsmanager:GetSecretValue'],
            'Resource': bootstrap_secret_arns,
        }
    )
    profile_policy = aws.iam.Policy(
        f'{self.name}-policy-nodeprofile',
        path='/',
        description='Policy for the Stalwart node instance profile',
        policy=json.dumps(profile_policy_doc),
    )
    arp = ASSUME_ROLE_POLICY.copy()
    arp['Statement'][0]['Principal']['Service'] = 'ec2.amazonaws.com'
    role = aws.iam.Role(
        f'{self.name}-role-nodeprofile',
        name=f'{self.name}-stalwart-node-profile',
        assume_role_policy=json.dumps(arp),
        path='/',
    )
    profile_attachment = aws.iam.RolePolicyAttachment(
        f'{self.name}-rpa-nodeprofile',
        role=role.name,
        policy_arn=profile_policy.arn,
    )
    profile = aws.iam.InstanceProfile(f'{self.name}-ip-nodeprofile', name=f'{self.name}-nodeprofile', role=role.name)

    return iam_user, profile_policy, role, profile_attachment, profile
