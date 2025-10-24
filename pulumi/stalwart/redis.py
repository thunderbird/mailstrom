"""
Small module to build Redis resources
"""

import pulumi
import tb_pulumi.elasticache
import tb_pulumi.secrets


def redis(
    self, redis_opts: dict,
) -> tuple[tb_pulumi.elasticache.ElastiCacheReplicationGroup, tb_pulumi.secrets.SecretsManagerSecret]:
    """Build Redis resources.

    :param redis_opts: Additional `ReplicationGroup
        <https://www.pulumi.com/registry/packages/aws/api-docs/elasticache/replicationgroup/#inputs>`_ inputs to pass
        into the Elasticache constructor.
    :type redis_opts: dict, optional

    :return: Tuple containing an ElastiCache Redis group and a Secrets Manager secret with the connection URL.
    :rtype: tuple[tb_pulumi.elasticache.ElastiCacheReplicationGroup, tb_pulumi.secrets.SecretsManagerSecret]
    """

    redis_group = tb_pulumi.elasticache.ElastiCacheReplicationGroup(
        name=f'{self.name}-redis',
        project=self.project,
        subnets=self.subnets,
        source_cidrs=[],
        source_sgids=[self.node_sgs[sg].resources['sg'].id for sg in self.node_sgs],
        opts=pulumi.ResourceOptions(parent=self, depends_on=[*self.node_sgs.values()]),
        tags=self.tags,
        **redis_opts,
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
