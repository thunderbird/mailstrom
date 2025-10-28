"""
Small module to build Redis resources
"""

import pulumi
import tb_pulumi.elasticache
import tb_pulumi.secrets


def redis(
    self, cache_node_type: str, cache_node_count: int, cache_parameters: list
) -> tuple[tb_pulumi.elasticache.ElastiCacheReplicationGroup, tb_pulumi.secrets.SecretsManagerSecret]:
    """Build Redis resources.

    :param cache_node_count: Number of Redis cluster nodes to build. This must be at least 1. When greater than 1, one
        primary "write" node will be created with (n - 1) read-only replicas. Defaults to 1.
    :type cache_node_count: int, optional

    :param cache_node_type: The `ElastiCache instance type
        <https://docs.aws.amazon.com/AmazonElastiCache/latest/dg/CacheNodes.SupportedTypes.html>`_ to use when building
        Redis cache nodes. Defaults to "cache.t3.micro".
    :type cache_node_type: str, optional

    :param cache_parameters: Dictionary of parameters in the parameter group to override.
    :type cache_parameters: dict, optional

    :return: Tuple containing an ElastiCache Redis group and a Secrets Manager secret with the connection URL.
    :rtype: tuple[tb_pulumi.elasticache.ElastiCacheReplicationGroup, tb_pulumi.secrets.SecretsManagerSecret]
    """

    redis_group = tb_pulumi.elasticache.ElastiCacheReplicationGroup(
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
    def __redis_secret(primary_address: str, reader_address: str):
        return tb_pulumi.secrets.SecretsManagerSecret(
            name=f'{self.name}-secret-redis',
            project=self.project,
            exclude_from_project=True,
            secret_name=f'mailstrom/{self.project.stack}/stalwart.postboot.redis_backend',
            secret_value=f'["redis://{primary_address}#insecure", "redis://{reader_address}#insecure"]',
            opts=pulumi.ResourceOptions(parent=self),
        )

    redis_secret = pulumi.Output.all(**redis_group.resources).apply(
        lambda redis_resources: pulumi.Output.all(
            primary=redis_resources['replication_group'].primary_endpoint_address,
            reader=redis_resources['replication_group'].reader_endpoint_address,
        ).apply(
            lambda addresses: __redis_secret(primary_address=addresses['primary'], reader_address=addresses['reader'])
        )
    )

    return redis_group, redis_secret
