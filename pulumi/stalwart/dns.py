import pulumi_cloudflare as cloudflare


def private_load_balancer_dns(self, top_level_domain, private_lbs):
    if self.project.stack in ['stage', 'prod']:
        cloudflare_zone_id = self.project.pulumi_config.require_secret('cloudflare_zone_id')
        return {
            service: cloudflare.DnsRecord(
                f'{self.name}-priv-{service}-dns',
                name=f'{self.project.name_prefix}-{service}-i.{top_level_domain}',
                ttl=60,
                type='CNAME',
                zone_id=cloudflare_zone_id,
                content=private_lbs[service].resources['load_balancer'].dns_name,
                proxied=False,
            )
            for service, lb in private_lbs.items()
        }
