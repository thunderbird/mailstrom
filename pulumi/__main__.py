#!/bin/env python3


import pulumi
import pulumi_aws as aws
import tb_pulumi
import tb_pulumi.cloudfront
import tb_pulumi.cloudwatch
import tb_pulumi.ec2
import tb_pulumi.elasticache
import tb_pulumi.network
import tb_pulumi.s3
import stalwart

from tb_pulumi.constants import CLOUDFRONT_CACHE_POLICY_ID_OPTIMIZED


project = tb_pulumi.ThunderbirdPulumiProject()
resources = project.config.get('resources')

# Store some Pulumi secrets in AWS
psm_opts = resources['tb:secrets:PulumiSecretsManager']['secrets']
psm = tb_pulumi.secrets.PulumiSecretsManager(
    name=f'{project.name_prefix}-psm',
    project=project,
    **psm_opts,
)

# Build out some private network space
vpc_opts = resources['tb:network:MultiCidrVpc']['vpc']
vpc = tb_pulumi.network.MultiCidrVpc(
    f'{project.name_prefix}-vpc',
    project,
    **vpc_opts,
)

# Build out SSH bastions if any are defined
bastions = {}
for bastion in resources['tb:ec2:SshableInstance'].keys():
    bastion_opts = resources['tb:ec2:SshableInstance'][bastion]
    bastions[bastion] = tb_pulumi.ec2.SshableInstance(
        f'{project.name_prefix}-{bastion}',
        project=project,
        subnet_id=vpc.resources['subnets'][0].id,
        vpc_id=vpc.resources['vpc'].id,
        opts=pulumi.ResourceOptions(depends_on=[vpc]),
        **bastion_opts,
    )


def __jumphost_rules(jumphosts):
    return [
        {
            'description': 'Allow SSH traffic from a jumphost',
            'protocol': 'tcp',
            'from_port': 22,
            'to_port': 22,
            'source_security_group_id': sgid,
        }
        for sgid in [jumphosts[jumphost].resources['security_group'].resources['sg'].id for jumphost in jumphosts]
    ]


jumphost_rules = pulumi.Output.all(**bastions).apply(lambda jumphosts: __jumphost_rules(jumphosts=jumphosts))


# Build a Stalwart cluster
def __stalwart_cluster(jumphost_rules: list[dict]):
    stalwart_opts = resources['tb:mailstrom:StalwartCluster']['thundermail']
    return stalwart.StalwartCluster(
        f'{project.name_prefix}-stalwart',
        project=project,
        subnets=vpc.resources['subnets'],
        node_additional_ingress_rules=jumphost_rules,
        opts=pulumi.ResourceOptions(depends_on=[vpc]),
        **stalwart_opts,
    )


project.resources['stalwart_cluster'] = jumphost_rules.apply(
    lambda jumphost_rules: __stalwart_cluster(jumphost_rules=jumphost_rules)
)

# Build an S3 website to host our autoconfig files in
project.resources['autoconfig_website'] = tb_pulumi.s3.S3BucketWebsite(
    f'{project.name_prefix}-autoconfig_site',
    project=project,
    **resources['tb:s3:S3BucketWebsite']['autoconfig'],
)

# Determine the bucket's domain name
website_bucket_regional_domain_name = (
    f'{resources["tb:s3:S3BucketWebsite"]["autoconfig"]["bucket_name"]}'
    f'.s3-website.{project.aws_region}.amazonaws.com'
)

# Create an Origin Access Control to use when CloudFront talks to S3
project.resources['autoconfig_oac'] = aws.cloudfront.OriginAccessControl(
    f'{project.name_prefix}-autoconfig_oac',
    origin_access_control_origin_type='s3',
    signing_behavior='always',
    signing_protocol='sigv4',
    description=f'Serve {project.name_prefix} autoconfig contents via CDN',
    name=resources['tb:s3:S3BucketWebsite']['autoconfig']['bucket_name'],
)

# Break configs out into distinct parts to make this cleaner
tb_distro_config = resources['tb:cloudfront:CloudFrontDistribution']['autoconfig']
aws_distro_config = tb_distro_config.pop('distribution', {})

# Define the distro's origin as an S3 website
website_origin = {
    'domain_name': website_bucket_regional_domain_name,
    'origin_id': website_bucket_regional_domain_name,
    # 'origin_access_control_id': project.resources['autoconfig_oac'].id,
    'custom_origin_config': {
        'http_port': 80,
        'https_port': 443,
        'origin_protocol_policy': 'http-only',
        'origin_ssl_protocols': ['SSLv3', 'TLSv1', 'TLSv1.1', 'TLSv1.2'],
    },
}
aws_distro_config['origins'] = [website_origin]

# Update (or create wholesale if necessary) the default cache behavior
default_cache_behavior = aws_distro_config.pop('default_cache_behavior', {})
default_cache_behavior.update(
    {
        'cache_policy_id': CLOUDFRONT_CACHE_POLICY_ID_OPTIMIZED,
        'target_origin_id': website_bucket_regional_domain_name,
    }
)
aws_distro_config['default_cache_behavior'] = default_cache_behavior

# Build the SSL cert config
certificate_arn = tb_distro_config.pop('certificate_arn', None)
aws_distro_config['viewer_certificate'] = {
    'acm_certificate_arn': certificate_arn,
    'minimum_protocol_version': 'TLSv1.2_2021',
    'ssl_support_method': 'sni-only',
}

# Build a CloudFront Distribution to serve autoconfig from edge locations and to terminate SSL
project.resources['cloudfront_distribution'] = tb_pulumi.cloudfront.CloudFrontDistribution(
    name=f'{project.name_prefix}-autoconfig_distro',
    project=project,
    distribution=aws_distro_config,
    tags=project.common_tags,
    opts=pulumi.ResourceOptions(
        depends_on=[project.resources['autoconfig_website'], project.resources['autoconfig_oac']]
    ),
    **tb_distro_config,
)

monitoring_opts = resources['tb:cloudwatch:CloudWatchMonitoringGroup']
monitoring = tb_pulumi.cloudwatch.CloudWatchMonitoringGroup(
    name=f'{project.name_prefix}-monitoring',
    project=project,
    notify_emails=monitoring_opts['notify_emails'],
    config=monitoring_opts,
)
