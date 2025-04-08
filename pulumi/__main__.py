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


stalwart_cluster = jumphost_rules.apply(lambda jumphost_rules: __stalwart_cluster(jumphost_rules=jumphost_rules))
