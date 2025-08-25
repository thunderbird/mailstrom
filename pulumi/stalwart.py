"""A tb_pulumi extension that builds a `Stalwart cluster <https://stalw.art/docs/get-started/>`_."""

import base64
import json
import pulumi
import pulumi_aws as aws
import tarfile
import tb_pulumi
import tb_pulumi.iam
import tb_pulumi.network
import tb_pulumi.s3
import tb_pulumi.secrets
import toml

from enum import Enum
from functools import cached_property
from jinja2 import Template
from tb_pulumi.constants import ASSUME_ROLE_POLICY, IAM_POLICY_DOCUMENT


#: Mapping of features of the https service and the API paths to enable for them
HTTPS_FEATURES = {
    'caldav': '/dav/cal,/dav/pal,/.well-known/caldav',
    'carddav': '/dav/card,/dav/pal,/.well-known/carddav',
    'jmap': '/jmap,/.well-known/jmap',
    'webdav': '/dav/files,/dav/pal',
}

#: Mapping of supported cluster services to their associated ports
STALWART_CLUSTER_SERVICES = {
    'all': None,
    'api': 8080,
    'https': 443,
    'imap': 143,
    'imaps': 993,
    'lmtp': 24,
    'management': 8080,
    'managesieve': 4190,
    'pop3': 110,
    'pop3s': 995,
    'smtp': 25,
    'smtps': 465,
    'submission': 587,
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
    """**Pulumi Type:** ``tb:mailstrom:StalwartCluster``

    Builds EC2 instances which operate as a Stalwart Mail Server cluster.

    Produces the following ``resources``:

        - *instances* - Dict of :py:class:`StalwartClusterNode`s, identified by their node_id.
        - *jmap_secret* - :py:class:`tb_pulumi.secrets.SecretsManagerSecret` containing the TOML-formatted JMAP config.
        - *lb* - :py:class:`StalwartLoadBalancer` defining the way service traffic is routed through the cluster.
        - *lb_sg* - :py:class:`tb_pulumi.network.SecurityGroupWithRules` created for the cluster's load balancer.
        - *node_profile* - The instance profile used for each cluster node.
        - *node_profile_policy* - The `aws.iam.Policy
          <https://www.pulumi.com/registry/packages/aws/api-docs/iam/policy/>`_ attached to the instance profile.
        - *node_profile_policy_attachment* - The `aws.iam.PolicyAttachment
          <https://www.pulumi.com/registry/packages/aws/api-docs/iam/policyattachment/>`_ resource between the the
          policy and the instance profile.
        - *node_sgs* - Dict of :py:class:`tb_pulumi.network.SecurityGroupWithRules` created for each node to support its
          enabled services, identified by their node_id.
        - *redis* - :py:class:`tb_pulumi.elasticache.ElastiCacheReplicationGroup` which Stalwart uses for its in-
          memory store.
        - *redis_secret* - :py:class:`tb_pulumi.secrets.SecretsManagerSecret` containing the Redis connection details.
        - *s3* - :py:class:`tb_pulumi.s3.S3Bucket` which Stalwart uses for its blob store.
        - *s3_policy* - `aws.iam.Policy <https://www.pulumi.com/registry/packages/aws/api-docs/iam/policy/>`_ granting
          full, unrestricted access to the S3 bucket and all its objects.
        - *s3_secret* - :py:class:`tb_pulumi.secrets.SecretsManagerSecret` containing the S3 bucket details.
        - *user- :py:class:`tb_pulumi.iam.UserWithAccessKey` which Stalwart itself will use to manipulate the objects in
          its S3 blob store.

    :param name: A string identifying this set of resources.
    :type name: str

    :param project: The ThunderbirdPulumiProject to add these resources to.
    :type project: tb_pulumi.ThunderbirdPulumiProject

    :param subnets: List of `aws.ec2.Subnet <https://www.pulumi.com/registry/packages/aws/api-docs/ec2/subnet/>`_ s
        in which to build cluster nodes.
    :type subnets: list[aws.ec2.Subnet]

    :param cache_node_count: Number of Redis cluster nodes to build. This must be at least 1. When greater than 1, one
        primary "write" node will be created with (n - 1) read-only replicas. Defaults to 1.
    :type cache_node_count: int, optional

    :param cache_node_type: The `ElastiCache instance type
        <https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheNodes.SupportedTypes.html>`_ to use when building
        Redis cache nodes. Defaults to "cache.t3.micro".
    :type cache_node_type: str, optional

    :param cache_parameters: Dictionary of parameters in the parameter group to override.
    :type cache_parameters: dict, optional

    :param https_features: List of features which Stalwart presents over the https service to enable across the cluster.
        These must match with keys in the HTTPS_FEATURES dict. Defaults to [].
    :type https_features: dict, optional

    :param jmap: Dictionary of options to configure the JMAP configuration on servers running JMAP. This should match
        the options listed in `Stalwart's JMAP documention <https://stalw.art/docs/jmap/overview>`_. A very brief
        and incomplete example:

        .. code-block: yaml

            jmap:
              protocol:
                request:
                    max-concurrent: 4
                    max-size: 10000000
                    max-calls: 16
                upload:
                    ttl: 1h
                    # ... etc

        Has no effect if ``jmap`` is not specified in ``https_features``.
    :type jmap: dict, optional

    :param load_balancer: Configuration for the load balancer, listing services to expose and what other components to
        expose them to. Must contain a `services` dict, whose keys must be valid :py:data:`STALWART_CLUSTER_SERVICES`.
        Those values must contain at least one (or both) of a list of ``source_cidrs`` or a list of
        ``source_security_group_ids``. For example:

        .. code-block:: yaml
            :linenos:

            load_balancer:
                services:
                    imap:
                        source_cidrs: ['0.0.0.0/0']
                    management:
                        source_security_group_ids: ['sg-abcdef0123456789']
                        source_cidrs: ['10.0.0.0/8']
    :type load_balancer: dict, optional

    :param nodes: Dict describing the individual nodes of the cluster. Each key is a node_id, which must be a
        stringified integer (a restriction imposed by Stalwart), and each value is a dict of supported values describing
        a node configuration. The configuration is composed of inputs to :py:meth:`StalwartCluster.node`. The values
        listed below are described in more detail alongside that function. The set of valid values is:

        - disable_api_stop: bool (False)
        - disable_api_termination: bool (False)
        - ignore_ami_changes: bool (True)
        - ignore_user_data_changes: bool (True)
        - instance_type: str (t3.micro)
        - node_roles: list[str] (['all'])
        - services: list[str] (['all'])
        - storage_capacity: int (20)

        Any additional arguments will be passed as inputs into the `aws.ec2.Instance
        <https://www.pulumi.com/registry/packages/aws/api-docs/ec2/instance/#inputs>`_ resource.
    :type nodes: dict, optional

    :param node_additional_ingress_rules: Dict describing additional ingress rules to apply to the node. This is useful
        for granting access to services from sources other than the load balancer. Defaults to {}.
    :type node_additional_ingress_rules: dict, optional

    :param stalwart_image: The Docker image to use for the Stalwart service. Defaults to
        'stalwartlabs/mail-server:v0.11'
    :type stalwart_image: str

    :param user_data_archive: File on disk in which to store the bzipped tar file for the user data bootstrapping stage.
        This is a temporary file which can be safely deleted after a Pulumi run. This file is intentionally not deleted,
        as it is valuable for debugging the bootstrapping process. However, any Pulumi command that uses this module
        will cause the creation of a new archive. This will overwrite any previously existing archive. Use this
        parameter to specify a different filename if you want to produce a special artifact for some reason. Defaults to
        "bootstrap.tbz".
    :type user_data_archive: str

    :param user_data_template: File on disk in which to find the Jinja2 template used to generate user data for each
        node in the cluster. Defaults to "stalwart_instance_user_data.sh.j2".
    :type user_data_template: str

    :param opts: Additional pulumi.ResourceOptions to apply to these resources. Defaults to None.
    :type opts: pulumi.ResourceOptions, optional

    :param tags: Key/value pairs to merge with the default tags which get applied to all resources in this group.
        Defaults to {}.
    :type tags: dict, optional

    :raises ValueError: When an empty list of subnets is provided.
    """

    def __init__(
        self,
        name: str,
        project: tb_pulumi.ThunderbirdPulumiProject,
        subnets: list[aws.ec2.Subnet],
        cache_node_count: int = 1,
        cache_node_type: str = 'cache.t3.micro',
        cache_parameters: list = [],
        https_features: list = [],
        jmap: dict = None,
        nodes: dict = {},
        node_additional_ingress_rules: list[dict] = [],
        public_load_balancer: dict = {},
        stalwart_image: str = 'stalwartlabs/mail-server:v0.11',
        user_data_archive: str = 'bootstrap.tbz',
        user_data_template: str = 'stalwart_instance_user_data.sh.j2',
        opts: pulumi.ResourceOptions = None,
        tags: dict = {},
    ):
        super().__init__(
            'tb:mailstrom:StalwartCluster',
            name=name,
            project=project,
            opts=opts,
            tags=tags,
        )

        # Sanity check the subnets list
        if len(subnets) == 0:
            raise ValueError('You must provide at least one subnet.')

        # Internalize some vars we need in the other functions and properties
        self.https_features = https_features
        self.public_load_balancer_config = public_load_balancer
        self.nodes = nodes
        self.stalwart_image = stalwart_image
        self.subnets = subnets
        self.user_data_archive = user_data_archive
        self.user_data_template = user_data_template

        # All subnets must be in the same VPC. For convenience, we grab the ID from the first subnet.
        self.vpc_id = self.subnets[0].vpc_id

        # Build custom security groups per node depending on cluster service config
        self.node_sgs = {
            node: self.node_security_group(node_id=node, additional_rules=node_additional_ingress_rules)
            for node in nodes
        }

        # Build a Redis cluster for Stalwart's in-memory store
        redis = tb_pulumi.elasticache.ElastiCacheReplicationGroup(
            name=f'{self.name}-redis',
            project=self.project,
            subnets=self.subnets,
            description=f'Redis cluster for {self.name}',
            engine='redis',
            engine_version='7.1',
            node_type=cache_node_type,
            num_cache_nodes=cache_node_count,
            parameter_group_family='redis7',
            parameter_group_params=cache_parameters,
            source_cidrs=[],
            source_sgids=[self.node_sgs[sg].resources['sg'].id for sg in self.node_sgs],
            opts=pulumi.ResourceOptions(parent=self, depends_on=[*self.node_sgs.values()]),
            tags=self.tags,
        )

        # Store Redis config details in Secrets Manager
        def __redis_secret(address: str):
            return tb_pulumi.secrets.SecretsManagerSecret(
                name=f'{name}-secret-redis',
                project=self.project,
                exclude_from_project=True,
                secret_name=f'mailstrom/{self.project.stack}/stalwart.postboot.redis_backend',
                secret_value=json.dumps({'urls': f'redis://{address}#insecure'}),
                opts=pulumi.ResourceOptions(parent=self),
            )

        redis_secret = pulumi.Output.all(**redis.resources).apply(
            lambda redis_resources: redis_resources['replication_group'].primary_endpoint_address.apply(
                lambda address: __redis_secret(address=address)
            )
        )

        # Build an S3 bucket for Stalwart's blob storage
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
            name=f'{name}-secret-s3',
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

        iam_user_name = f'{self.project.name_prefix}-stalwart'
        iam_user = tb_pulumi.iam.UserWithAccessKey(
            name=f'{name}-user',
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
        profile = aws.iam.InstanceProfile(
            f'{self.name}-ip-nodeprofile', name=f'{self.name}-nodeprofile', role=role.name
        )

        # Store a TOML version of the JMAP config in Secrets Manager for nodes to read back later
        jmap_dict = {'jmap': jmap} if jmap else {}  # Ensure every TOML option gets the "jmap" text in it
        toml_str = toml.dumps(jmap_dict) if jmap else ''
        jmap_secret = tb_pulumi.secrets.SecretsManagerSecret(
            name=f'{self.name}-secret-jmap',
            project=self.project,
            exclude_from_project=True,
            secret_name=f'{self.project.project}/{self.project.stack}/stalwart.postboot.jmap_toml',
            secret_value=toml_str,
            opts=pulumi.ResourceOptions(parent=self),
        )

        # Pipe the node configs into a series of StalwartClusterNodes
        instances = {}
        for idx, node_id in enumerate(nodes):
            subnet = self.subnets[idx % len(self.subnets)]
            instances[node_id] = self.node(
                node_id=node_id,
                subnet=subnet,
                iam_instance_profile=profile.name,
                depends_on=[jmap_secret, profile, redis_secret, s3_secret, subnet],
                **nodes[node_id],
            )

        public_lb_sg_id = pulumi.Output.all(**self.public_load_balancer_security_group.resources).apply(
            lambda resources: resources['sg'].id
        )
        if self.expose_all_services:
            public_lb_services = {
                service: self.public_load_balancer_config['services']['all']
                for service, port in STALWART_CLUSTER_SERVICES.items()
                if port is not None
            }
        else:
            public_lb_services = self.public_load_balancer_config['services']

        public_lb = StalwartLoadBalancer(
            name=f'{self.project.project}-{self.project.stack}',  # AWS imposes a 32-character max on this
            project=self.project,
            instances=instances,
            node_config=self.nodes,
            security_group_ids=[public_lb_sg_id],
            service_config=public_lb_services,
            subnets=self.subnets,
            excluded_nodes=self.public_load_balancer_config['excluded_nodes']
            if 'excluded_nodes' in self.public_load_balancer_config
            else None,
            opts=pulumi.ResourceOptions(parent=self, depends_on=[self.public_load_balancer_security_group]),
            tags=self.tags,
        )

        self.finish(
            resources={
                'instances': instances,
                'jmap_secret': jmap_secret,
                'public_lb': public_lb,
                'public_lb_sg': self.public_load_balancer_security_group,
                'node_profile': profile,
                'node_profile_policy': profile_policy,
                'node_profile_policy_attachment': profile_attachment,
                'node_sgs': self.node_sgs,
                'redis': redis,
                'redis_secret': redis_secret,
                's3': s3_bucket,
                's3_policy': s3_policy,
                's3_secret': s3_secret,
                'user': iam_user,
            }
        )

    # Cache this property because it produces a Pulumi resource. We don't want to define that multiple times.
    @cached_property
    def public_load_balancer_security_group(self):
        """Defines a security group for the load balancer based on the load_balancer config options."""

        # Build a skeleton for the security group rules, allowing all egress
        lb_sg_rules = {
            'egress': [
                {
                    'description': 'Allow traffic outbound from the load balancer',
                    'protocol': 'tcp',
                    'from_port': 0,
                    'to_port': 65535,
                    'cidr_blocks': ['0.0.0.0/0'],
                }
            ],
            'ingress': [],
        }

        # Determine an explicit list of services, expanding the "all" shorthand into a complete list
        if self.expose_all_services:
            # "All services" means everything in the list except for "all" itself
            exposed_services = STALWART_CLUSTER_SERVICES.copy()
            del (exposed_services)['all']
        else:
            exposed_services = self.public_load_balancer_config['services'].keys()

        for service in exposed_services:
            # Validate each exposed service's name
            if service not in STALWART_CLUSTER_SERVICES:
                raise ValueError(f'{service} is not a valid Stalwart cluster service.')

            # Determine which service config to use; the "all" service applies to all services
            if self.expose_all_services:
                service_config = self.public_load_balancer_config['services']['all']
            else:
                service_config = self.public_load_balancer_config['services'][service]

            # Create one rule including all source_cidrs we need to open access to
            if 'source_cidrs' in service_config:
                lb_sg_rules['ingress'].append(
                    {
                        'description': f'Allow {service} traffic',
                        'protocol': 'tcp',
                        'from_port': STALWART_CLUSTER_SERVICES[service],
                        'to_port': STALWART_CLUSTER_SERVICES[service],
                        'cidr_blocks': service_config['source_cidrs'],
                    }
                )

            # Create one rule for each source security group since AWS doesn't allow lists of them
            if 'source_security_group_ids' in service_config:
                for sgid in self.public_load_balancer_config['services'][service]['source_security_group_ids']:
                    lb_sg_rules['ingress'].append(
                        {
                            'description': f'Allow {service} traffic',
                            'protocol': 'tcp',
                            'from_port': STALWART_CLUSTER_SERVICES[service],
                            'to_port': STALWART_CLUSTER_SERVICES[service],
                            'source_security_group_id': sgid,
                        }
                    )

        # Pipe the whole rule config into a SecurityGroupWithRules pattern
        return tb_pulumi.network.SecurityGroupWithRules(
            name=f'{self.name}-lbsg',
            project=self.project,
            rules=lb_sg_rules,
            vpc_id=self.vpc_id,
            opts=pulumi.ResourceOptions(parent=self),
            tags=self.tags,
        )

    def node_security_group(
        self, node_id: str, additional_rules: list[dict]
    ) -> tb_pulumi.network.SecurityGroupWithRules:
        """Build an instance-dedicated security group with rules specific to the services available on the machine.

        :param node_id: The node_id of the node to build a security group for.
        :type node_id: str

        :param additional_rules: List of security group rule configurations to apply to the node in addition to the ones
            opened for the Stalwart services.
        :type additional_rules: list[dict]

        :return: A :py:class:`tb_pulumi.network.SecurityGroupWithRules` for the node.
        :rtype: tb_pulumi.network.SecurityGroupWithRules
        """

        # Start with a skeleton for the security group rules, allowing all egress
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
            'ingress': [
                {
                    'description': 'Allow the nodes to speak the Stalwart gossip protocol amongst themselves',
                    'protocol': 'udp',
                    'from_port': 1179,
                    'to_port': 1179,
                    'self': True,
                }
            ],
        }

        # Expand "all" services into an explicit list of services
        if node_handles_all_services(services=self.nodes[node_id]['services']):
            # "All" services means everything except "all" itself
            handled_services = STALWART_CLUSTER_SERVICES.copy()
            del handled_services['all']
        else:
            # Build for whatever more specific services the user supplied
            handled_services = self.nodes[node_id]['services']

        # Expose each service port, but only to the load balancer
        for service in handled_services:
            sg_rules['ingress'].append(
                {
                    'description': f'Allow {service} traffic',
                    'protocol': 'tcp',
                    'from_port': STALWART_CLUSTER_SERVICES[service],
                    'to_port': STALWART_CLUSTER_SERVICES[service],
                    'source_security_group_id': self.public_load_balancer_security_group.resources['sg'].id,
                }
            )

        sg_rules['ingress'].extend(additional_rules)

        # Feed the rules config into a SecurityGroupWithRules pattern
        return tb_pulumi.network.SecurityGroupWithRules(
            name=f'{self.name}-{node_id}-sg',
            project=self.project,
            rules=sg_rules,
            vpc_id=self.vpc_id,
        )

    def node(
        self,
        node_id: str,
        subnet: aws.ec2.Subnet,
        depends_on: list = [],
        disable_api_stop: bool = False,
        disable_api_termination: bool = False,
        ignore_ami_changes: bool = True,
        ignore_user_data_changes: bool = True,
        instance_type: str = 't3.micro',
        node_roles: list[str] = ['all'],
        services: list[str] = ['all'],
        storage_capacity: int = 20,
        **kwargs,
    ) -> aws.ec2.Instance:
        """Builds a Stalwart node represented by the configuration for the given node_id.

        :param node_id: The unique node_id to identify the node in the cluster. This must be a stringified integer.
        :type node_id: str

        :param subnet: The subnet to build the node in.
        :type subnet: aws.ec2.Subnet

        :param disable_api_stop: When True, prevents AWS API calls from stopping the instance. Defaults to False.
        :type disable_api_stop: bool, optional

        :param disable_api_termination: When True, prevents AWS API calls from terminating the instance. Defaults to
            False.
        :type disable_api_termination: bool, optional

        :param ignore_ami_changes: When True, changes to the instance's AMI will not be applied. This prevents unwanted
            rebuilding of cluster nodes, potentially causing downtime. Set to False if the AMI has changed and you
            intend on rebuilding the node. Defaults to True.
        :type ignore_ami_changes: bool, optional

        :param ignore_user_data_changes: When True, changes to the instance's user data will not be applied. In order to
            apply user data, the instance must be stopped and later restarted. This means that changes to the bootstrap
            process could lead to entire environments being turned off and back on again if this setting is not enabled.
            To prevent unwanted downtime, keep this enabled. Defaults to True.
        :type ignore_user_data_changes: bool, optional

        :param instance_type: `AWS EC2 instance type <https://aws.amazon.com/ec2/instance-types/>`_ to build the node
            on. Defaults to 't3.micro'.
        :type instance_type: str, optional

        :param node_roles: List of :py:class:`StalwartNodeRoles` to enable on the node. Defaults to ['all'].
        :type node_roles: list[str], optional

        :param services: List of services to run on the node. Defaults to ['all'].
        :type services: list[str]

        :param storage_capacity: Size of the ephemeral disk on the node in GB. Defaults to 20.
        :type storage_capacity: int, optional

        :return: The EC2 instance running the Stalwart node.
        :rtype: aws.ec2.Instance
        """

        # Expand the "all" cluster service into an explicit list of services to run on the node
        if node_handles_all_services(services=services):
            node_services = STALWART_CLUSTER_SERVICES.copy()
            del node_services['all']
        else:
            node_services = self.nodes[node_id]['services']
        node_services_tag = ','.join(node_services)

        # Expand the "all" node role into an explicit list
        if node_handles_all_roles(node_roles=node_roles):
            node_roles_tag = ','.join([key.lower() for key in StalwartNodeRoles.__members__.keys() if key != 'ALL'])
        else:
            node_roles_tag = ','.join([role.lower() for role in self.nodes[node_id]['node_roles']])

        # Refuse to proceed if we don't recognize an https feature
        invalid_features = [feature for feature in self.https_features if feature not in HTTPS_FEATURES]
        if invalid_features:
            raise ValueError(f'Invalid HTTPS feature(s) provided: {invalid_features}')

        # Some features require multiple paths; some of those paths overlap. Here we join and then split them again
        # then convert them to a set, which only contains unique paths.
        https_paths = sorted(set(','.join([HTTPS_FEATURES[feature] for feature in self.https_features]).split(',')))

        # These tags will later get read back when the instance comes online by the postboot process
        postboot_tags = {
            'postboot.stalwart.aws_region': self.project.aws_region,
            'postboot.stalwart.env': self.project.stack,
            'postboot.stalwart.https_paths': ','.join(https_paths),
            'postboot.stalwart.image': self.stalwart_image,
            'postboot.stalwart.node_services': node_services_tag,
            'postboot.stalwart.node_id': node_id,
            'postboot.stalwart.node_roles': node_roles_tag,
        }

        # Combine all the tags
        instance_tags = self.tags.copy()
        instance_tags.update({'Name': f'{self.name}-{node_id}'})
        instance_tags.update(postboot_tags)

        # Sometimes we want to not apply changes to the AMI or user data, which would cause downtime. These features are
        # exposed through the component resource so users can more carefully control deployments.
        instance_ignores = []
        if ignore_ami_changes:
            instance_ignores.append('ami')
        if ignore_user_data_changes:
            instance_ignores.append('user_data')

        return aws.ec2.Instance(
            f'{self.name}-{node_id}-instance',
            ami=self.project.get_latest_amazon_linux_ami(),
            associate_public_ip_address=True,  # These are private, but a public IP assignment is required for egress
            disable_api_stop=disable_api_stop,
            disable_api_termination=disable_api_termination,
            instance_type=instance_type,
            metadata_options={  # Enabling this allows us to access tags via the instance metadata service
                'instance_metadata_tags': 'enabled',  # This is a hard requirement for the bootstrap process
            },
            root_block_device={
                'delete_on_termination': True,
                'encrypted': True,
                'tags': self.tags,
                'volume_size': storage_capacity,
                'volume_type': 'gp2',
            },
            subnet_id=subnet.id,
            tags=instance_tags,
            user_data=self.user_data,
            vpc_security_group_ids=[self.node_sgs[node_id].resources['sg'].id],
            opts=pulumi.ResourceOptions(parent=self, ignore_changes=instance_ignores, depends_on=depends_on),
            **kwargs,
        )

    @property
    def user_data(self):
        """So called "user data" is a script or cloud-init config that will get run on an EC2 instance right as it boots
        for the first time. This can be used to bootstrap a server, as we do here. This property injects a base64-
        encoded zip file of all the things the instance needs for bootstrapping into a user data script used to
        configure a new Stalwart node.
        """

        # Produce a zip file containing the contents of the bootstrap directory. "arcname" is used to prevent the
        # creation of a "bootstrap" subdirectory. We also choose the highest compression level because user data can't
        # exceed a certain size.
        archive_file_base = './bootstrap'
        archive_files = [
            'bootstrap.py',
            'templates/ports.j2',
            'templates/stalwart.toml.j2',
            'templates/thundermail.service.j2',
            'requirements.txt',
        ]
        with tarfile.open(self.user_data_archive, 'w:bz2') as archive:
            for file in archive_files:
                source_name = f'{archive_file_base}/{file}'
                archive.add(source_name, arcname=file)

        # Now read that file back in and base64-encode it
        with open(self.user_data_archive, 'rb') as archive_fh:
            archive_data = archive_fh.read()
        encoded_archive = base64.b64encode(archive_data).decode('utf8')

        # Do a minimal-effort Jinja template rendering of the user data
        with open(self.user_data_template, 'r') as fh:
            user_data_jinja = fh.read()
            user_data_values = {'bootstrap_tbz_base64': encoded_archive}
            template = Template(user_data_jinja)
            user_data = template.render(user_data_values)

        # Use for debugging the user data
        with open('user_data.sh', 'w') as fh:
            fh.write(user_data)

        return user_data

    # Cache this property because we don't need to validate/calculate this ever time we call it, just once
    @cached_property
    def expose_all_services(self) -> bool:
        """Determines if the public load balancer configuration is set to expose all services uniformly.

        :raises ValueError: When an invalid load balancer configuration is provided for the node.

        :rtype: bool
        """

        # Get the list of exposed services
        if 'services' not in self.public_load_balancer_config:
            raise ValueError('`public_load_balancer` option must contain a `services` entry.')
        services = self.public_load_balancer_config['services']

        # Determine if all services are exposed
        all_services = False
        if 'all' in services:
            if len(services) > 1:
                raise ValueError('When the "all" service is enabled, no other services may be.')
            all_services = True

        # Validate the rest of the config while we're at it
        for service in services:
            svc = services[service]
            if 'source_cidrs' not in svc and 'source_security_group_ids' not in svc:
                raise ValueError(
                    f'At least one of `source_cidrs` or `source_security_group_ids` must be set for service {service}.'
                )

        return all_services


class StalwartLoadBalancer(tb_pulumi.ThunderbirdComponentResource):
    """**Pulumi Type:** ``tb:mailstrom:StalwartLoadBalancer``

    Builds a network load balancer and related resources for routing traffic through a StalwartCluster.

    Produces the following ``resources``:

        - *listeners* - Dict of `aws.lb.Listeners <https://www.pulumi.com/registry/packages/aws/api-docs/lb/listener/>`_
          on the load balancer, one entry for each exposed service.
        - *load_balancer* - The `aws.lb.LoadBalancer
          <https://www.pulumi.com/registry/packages/aws/api-docs/lb/loadbalancer/>`_ routing traffic for the cluster.
        - *target_groups* - Dict of `aws.lb.TargetGroups
          <https://www.pulumi.com/registry/packages/aws/api-docs/lb/targetgroup/>`_ which receive the traffic, one entry
          for each exposed service.
        - *target_group_attachments* - Dict of `aws.lb.TargetGroupAttachments
          <https://www.pulumi.com/registry/packages/aws/api-docs/lb/targetgroupattachment/>`_ binding the targets to
          their target groups.

        :param name: A string identifying this set of resources.
        :type name: str

        :param project: The ThunderbirdPulumiProject to add these resources to.
        :type project: tb_pulumi.ThunderbirdPulumiProject

        :param instances: Dict of `aws.ec2.Instances
        <https://www.pulumi.com/registry/packages/aws/api-docs/ec2/instance/>`_, identified by their node IDs, which
        run any services requiring load balancing.
        :type instances: dict

        :param node_config: The ``nodes`` portion of a StalwartCluster's configuration. Relevant to this class is the
        list of configured services for each node, used to establish the correct targets for each load balancer
        listener.
        :type node_config: dict

        :param security_group_ids: List of security group IDs which should be attached to the load balancer.
        :type security_group_ids: list[str]

        :param service_config: The ``services`` section of the StalwartCluster's ``load_balancer`` configuration. This
        defines services which should be exposed through the load balancer, and to what audience they should be exposed.
        Use ``source_cidrs`` and ``source_security_group_ids`` to define that scope.
        :type service_config: dict

        :param subnets: List of subnets to attach the load balancer to. This list must be inclusive of all subnets in
        which you have targets. Targets that live in a subnet not contained in this list will be incapable of receiving
        load balanced traffic. All subnets must reside in the same VPC. The VPC ID will be determined from the first
        subnet listed.
        :type subnets: list[aws.ec2.Subnet]

        :param excluded_nodes: List of node IDs which should not receive any traffic at all. Instances in rotation which
        are added to this list will be removed from all target groups they are currently in. This allows for safe
        downtime operations on the cluster. Defaults to [].
        :type excluded_nodes: list[str], optional

        :param opts: Additional pulumi.ResourceOptions to apply to these resources. Defaults to None.
        :type opts: pulumi.ResourceOptions, optional

        :param tags: Key/value pairs to merge with the default tags which get applied to all resources in this group.
            Defaults to {}.
        :type tags: dict, optional

    """

    def __init__(
        self,
        name: str,
        project: tb_pulumi.ThunderbirdPulumiProject,
        instances: dict,
        node_config: dict,
        security_group_ids: list[str],
        service_config: dict,
        subnets: list[aws.ec2.Subnet],
        excluded_nodes: list[str] = [],
        opts: pulumi.ResourceOptions = None,
        tags: dict = {},
    ):
        super().__init__(
            'tb:mailstrom:StalwartLoadBalancer',
            name=name,
            project=project,
            opts=opts,
            tags=tags,
        )

        # Build a single load balancer
        load_balancer = aws.lb.LoadBalancer(
            f'{self.name}-lb',
            name=f'{self.name}-stalwart',
            enable_cross_zone_load_balancing=True,
            internal=False,
            load_balancer_type='network',
            security_groups=security_group_ids,
            subnets=[subnet.id for subnet in subnets],
            tags=self.tags,
            opts=pulumi.ResourceOptions(parent=self, depends_on=[*subnets]),
        )

        # Build a target group for each service
        target_groups = {
            service: aws.lb.TargetGroup(
                f'{self.name}-tg-{service}',
                health_check={
                    'enabled': True,
                    'healthy_threshold': 2,
                    'interval': 15,
                    'port': STALWART_CLUSTER_SERVICES[service],
                    'protocol': 'TCP',
                    'unhealthy_threshold': 2,
                },
                name=f'{self.project.stack}-{service}',  # Constrained to 32 characters
                port=STALWART_CLUSTER_SERVICES[service],
                protocol='TCP',
                target_type='instance',
                tags=self.tags,
                vpc_id=subnets[0].vpc_id,
                opts=pulumi.ResourceOptions(parent=self),
            )
            for service, config in service_config.items()
        }

        # For each target group, register nodes with matching services; route traffic through listeners
        target_group_attachments = {}
        listeners = {}
        for service, tg in target_groups.items():
            for node_id, node in node_config.items():
                if (
                    node_handles_all_services(services=node['services']) or service in node['services']
                ) and node_id not in excluded_nodes:
                    target_group_attachments[service] = aws.lb.TargetGroupAttachment(
                        f'{self.name}-tga-{service}-node{node_id}',
                        target_group_arn=tg.arn,
                        target_id=instances[node_id].id,
                        port=STALWART_CLUSTER_SERVICES[service],
                        opts=pulumi.ResourceOptions(
                            parent=self, depends_on=[*instances.values(), *target_groups.values()]
                        ),
                    )
            listeners[service] = aws.lb.Listener(
                f'{self.name}-listener-{service}',
                default_actions=[
                    {
                        'type': 'forward',
                        'target_group_arn': tg.arn,
                    }
                ],
                load_balancer_arn=load_balancer.arn,
                port=STALWART_CLUSTER_SERVICES[service],
                protocol='TCP',
                tags=self.tags,
                opts=pulumi.ResourceOptions(parent=self, depends_on=[*target_groups.values(), load_balancer]),
            )

        self.finish(
            resources={
                'listeners': listeners,
                'load_balancer': load_balancer,
                'target_groups': target_groups,
                'target_group_attachments': target_group_attachments,
            }
        )


def node_handles_all_roles(node_roles: list[str]) -> bool:
    """Determines if the given node is configured to handle all node roles.

    :param node_id: The node_id of the node to check.
    :type node_id: str

    :raises ValueError: When an invalid node role configuration is provided for the node.

    :rtype: bool
    """

    if len(node_roles) > 1 and 'all' in node_roles:
        raise ValueError('If the "all" node role is set for a node, no other roles may be set.')

    return True if len(node_roles) == 1 and 'all' in node_roles else False


def node_handles_all_services(services: list[str]) -> bool:
    """Determines if the given node is configured to handle all node services.

    :param node_id: The node_id of the node to check.
    :type node_id: str

    :raises ValueError: When an invalid cluster service configuration is provided for the node.

    :rtype: bool
    """

    if len(services) > 1 and 'all' in services:
        raise ValueError('If the "all" cluster service is set for a node, no other services may be set.')
    for service in services:
        if service.lower() not in STALWART_CLUSTER_SERVICES.keys():
            raise ValueError(f'"{service}" is not a valid cluster service.')

    return True if len(services) == 1 and 'all' in services else False
