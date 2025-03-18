#!/bin/env python3

import pulumi
import tb_pulumi
import tb_pulumi.ec2
import tb_pulumi.elasticache
import tb_pulumi.network
import stalwart


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

# Build a Stalwart cluster
redis_opts = resources['tb:elasticache:ElastiCacheReplicationGroup']['stalwart']
stalwart_opts = resources['tb:mailstrom:StalwartCluster']['thundermail']
stalwart_cluster = stalwart.StalwartCluster(
    f'{project.name_prefix}-stalwart',
    project=project,
    subnets=vpc.resources['subnets'],
    opts=pulumi.ResourceOptions(depends_on=[vpc]),
    **stalwart_opts,
)

# Build a jumphost so I can test things
jumphosts = {}
for jumphost in resources['tb:ec2:SshableInstance'].keys():
    jumphost_opts = resources['tb:ec2:SshableInstance'][jumphost]
    jumphosts[jumphost] = tb_pulumi.ec2.SshableInstance(
        f'{project.name_prefix}-{jumphost}',
        project=project,
        subnet_id=vpc.resources['subnets'][0].id,
        vpc_id=vpc.resources['vpc'].id,
        opts=pulumi.ResourceOptions(depends_on=[vpc]),
        **jumphost_opts,
    )
