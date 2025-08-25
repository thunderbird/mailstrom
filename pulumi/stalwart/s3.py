"""
Small module to build out our S3 needs.
"""

import json
import pulumi
import pulumi_aws as aws
import tb_pulumi.s3
import tb_pulumi.secrets

from tb_pulumi.constants import IAM_POLICY_DOCUMENT


def s3(self) -> tuple[tb_pulumi.s3.S3Bucket, tb_pulumi.secrets.SecretsManagerSecret, aws.iam.Policy]:
    """Build Stalwart S3 components.

    :return: Tuple with the S3 Bucket, secret with the bucket name and region, and IAM policy granting access to the
        bucket.
    :rtype: tuple[tb_pulumi.s3.S3Bucket, tb_pulumi.secrets.SecretsManagerSecret, aws.iam.Policy]
    """

    bucket_name = f'{self.name}-s3-store'
    s3_bucket = tb_pulumi.s3.S3Bucket(
        name=bucket_name,
        project=self.project,
        bucket_name=bucket_name,
        enable_server_side_encryption=True,
        enable_versioning=True,
        opts=pulumi.ResourceOptions(parent=self),
        tags=self.tags,
    )

    # Build a secret to store the Stalwart S3 config details in
    s3_secret = tb_pulumi.secrets.SecretsManagerSecret(
        name=f'{self.name}-secret-s3',
        project=self.project,
        exclude_from_project=True,
        secret_name=f'mailstrom/{self.project.stack}/stalwart.postboot.s3_backend',
        secret_value=json.dumps(
            {
                'bucket': bucket_name,
                'region': self.project.aws_region,
            }
        ),
        opts=pulumi.ResourceOptions(parent=self),
    )

    # Build an IAM policy granting bucket access
    def __s3_policy(bucket_arn: str, bucket_name: str):
        policy_doc = IAM_POLICY_DOCUMENT.copy()
        policy_doc['Statement'][0]['Sid'] = 'AllowFullS3Access'
        policy_doc['Statement'][0].update(
            {
                'Action': ['s3:*'],
                'Resource': [bucket_arn, f'{bucket_arn}*'],
            }
        )
        return aws.iam.Policy(
            f'{self.name}-policy-s3',
            name=f's3-full-access-{bucket_name}',
            path='/',
            description=f'Grants full acccess to the {bucket_name} S3 bucket and its contents',
            policy=json.dumps(policy_doc),
        )

    # Build an IAM policy granting bucket access
    s3_policy = pulumi.Output.all(bucket_arn=s3_bucket.resources['bucket'].arn, bucket_name=s3_bucket.name).apply(
        lambda outputs: __s3_policy(bucket_arn=outputs['bucket_arn'], bucket_name=outputs['bucket_name'])
    )

    return s3_bucket, s3_secret, s3_policy
