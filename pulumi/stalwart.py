"""Infrastructural patterns related to `Stalwart Mail Server <https://stalw.art/docs/get-started/>`_"""

import pulumi
import pulumi_aws as aws
import tb_pulumi
import tb_pulumi.network

from enum import Enum


#: Mapping of supported cluster services and their associated ports
STALWART_CLUSTER_SERVICES = {
    'http': 8080,
    'imap': 143,
    'imaps': 993,
    'lmtp': 24,
    'managesieve': 4190,
    'pop3': 110,
    'pop3s': 995,
    'smtp': 25,
    'smtps': 587,
}

class StalwartNodeRoles(Enum):
    """Discrete set of supported Stalwart cluster node roles."""

    ALL = 0
    ACME_RENEW = 1
    METRICS_CALCULATE = 2
    METRICS_PUSH = 3
    PURGE_ACCOUNTS = 4
    PURGE_STORES = 5


class StalwartCluster(tb_pulumi.ThunderbirdComponentResource):
    """**Pulumi Type:** ``tb:accounts:StalwartCluster``

    Builds EC2 instances which operate as a Stalwart Mail Server cluster.

    Produces the following ``resources``:

        - *whatever* - Something
    """

    def __init__(
        self,
        name: str,
        project: tb_pulumi.ThunderbirdPulumiProject,
        vpc_id: str,
        nodes: dict = {},
        services: dict = {},
        exclude_from_project: bool = False,
        opts: pulumi.ResourceOptions = None,
        tags: dict = {},
        **kwargs,
    ):
        super().__init__('tb:accounts:StalwartCluster', name=name, project=project, opts=opts, tags=tags)

        # First build the security group we will use on our load balancer
        lb_sg_rules = {
            'egress': [{
                'description': 'Allow traffic outbound from the load balancer',
                'protocol': 'tcp',
                'from_port': 0,
                'to_port': 65535,
                'cidr_blocks': ['0.0.0.0/0'],
            }],
            'ingress': [],
        }

        # Build a list of security group rules for the load balancer based on the config
        for service in services:
            if service not in STALWART_CLUSTER_SERVICES:
                raise ValueError(f'{service} is not a valid Stalwart cluster service.')
            if 'source_cidrs' in services[service]:
                lb_sg_rules['ingress'].append({
                    'description': f'Allow {service} traffic by IP',
                    'protocol': 'tcp',
                    'from_port': STALWART_CLUSTER_SERVICES[service],
                    'to_port': STALWART_CLUSTER_SERVICES[service],
                    'cidr_blocks': services[service]['source_cidrs']
                })
            if 'source_security_group_ids' in services[service]:
                for sgid in services[service]['source_security_group_ids']:
                    lb_sg_rules['ingress'].append({
                        'description': f'Allow {service} traffic from {sgid}',
                        'protocol': 'tcp',
                        'from_port': STALWART_CLUSTER_SERVICES[service],
                        'to_port': STALWART_CLUSTER_SERVICES[service],
                        'source_security_group_id': sgid,
                    })
        
        lb_sg = tb_pulumi.network.SecurityGroupWithRules(
            name=f'{name}-lbsg',
            project=project,
            rules=lb_sg_rules,
            vpc_id=vpc_id,
            opts=pulumi.ResourceOptions(parent=self),
            tags=self.tags,
        )

        instances = {}
        # for node_id in nodes:
        #     instances[node_id] = StalwartClusterNode(
        #         name='f{name}-{node_id}',
        #         project=project,
        #         opts=opts,
        #         tags=tags,
        #         exclude_from_project=True,
        #         **nodes[node_id],
        #     )

        self.finish(resources={'lb_sg': lb_sg, 'instances': instances})


class StalwartClusterNode(tb_pulumi.ThunderbirdComponentResource):
    """**Pulumi Type:** ``tb:accounts:StalwartClusterNode``

    Builds an EC2 instance and a security group setup for a single cluster instance's needs.

    Produces the following ``resources``:

        - *whatever* - Something

    :param exclude_from_project: When ``True`` , this prevents this component resource from being registered directly
        with the project. This does not prevent the component resource from being discovered by the project's
        ``flatten`` function, provided that it is nested within some resource that is not excluded from the project.
    :type exclude_from_project: bool, optional

    """

    def __init__(
        self,
        name: str,
        project: tb_pulumi.ThunderbirdPulumiProject,
        load_balancer_security_group_id: str,
        vpc_id: str,
        cluster_services: list[str] = ['all'],
        instance_type: str = 't2.micro',
        storage_capacity: int = 20,
        node_roles: list[str] = ['all'],
        exclude_from_project: bool = False,
        opts: pulumi.ResourceOptions = None,
        tags: dict = {},
    ):
        super().__init__('tb:accounts:StalwartClusterNode', name=name, project=project, opts=opts, tags=tags)

        # Sanity check the node role values
        if len(node_roles) > 1 and 'all' in node_roles:
            raise ValueError('If the "all" node role is set for a node, no other roles may be set.')
        for role in node_roles:
            if role.upper not in StalwartNodeRoles.__members__.keys():
                raise ValueError(f'"{role}" is not a valid node role.')

        # Sanity check the node service values
        if len(cluster_services) > 1 and 'all' in cluster_services:
            raise ValueError('If the "all" node service is set for a node, no other services may be set.')
        for service in cluster_services:
            if service.upper not in STALWART_CLUSTER_SERVICES.keys():
                raise ValueError(f'"{service}" is not a valid node service.')

        # Build an instance-dedicated security group with rules specific to the services available on the machine
        sg_rules = {
            'egress': [
                {
                    'description': 'Allow traffic from the instance out to the Internet',
                    'protocol': 'tcp',
                    'from_port': 0,
                    'to_port': 65535,
                    'cidr_blocks': ['0.0.0.0/0'],
                }
            ],
            'ingress': [],
        }

        # TODO: Need to build the load balancer's SG first so we can use its sgid as a source
        for service in cluster_services:
            sg_rules['ingress'].append({
                'description': f'Allow {service} traffic',
                'protocol': 'tcp',
                'from_port': STALWART_CLUSTER_SERVICES[service],
                'to_port': STALWART_CLUSTER_SERVICES[service],
                'source_security_group_id': load_balancer_security_group_id,
            })

        sg = tb_pulumi.network.SecurityGroupWithRules(
            name=f'{name}-sg',
            project=project,
            rules=sg_rules,
        )

        # Tags for the instance that inform behavior in the Ansible playbook
        ansible_tags = {
            'ansible.stalwart.cluster_services': cluster_services,
            'ansible.stalwart.node_roles': node_roles,
        }

        instance_tags = self.tags
        instance_tags.update(ansible_tags)

        self.finish(resources={})
