import json
import pulumi
import tb_pulumi.elasticache

def redis(self, cache_node_type: str, cache_node_count: int, cache_parameters: list):
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
    def __redis_secret(address: str):
        return tb_pulumi.secrets.SecretsManagerSecret(
            name=f'{self.name}-secret-redis',
            project=self.project,
            exclude_from_project=True,
            secret_name=f'mailstrom/{self.project.stack}/stalwart.postboot.redis_backend',
            secret_value=json.dumps({'urls': f'redis://{address}#insecure'}),
            opts=pulumi.ResourceOptions(parent=self),
        )

    redis_secret = pulumi.Output.all(**redis_group.resources).apply(
        lambda redis_resources: redis_resources['replication_group'].primary_endpoint_address.apply(
            lambda address: __redis_secret(address=address)
        )
    )

    return redis_group, redis_secret

