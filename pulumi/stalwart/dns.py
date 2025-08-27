import pulumi_cloudflare as cloudflare

def private_load_balancer_dns(self, private_lbs):
    cloudflare_zone_id = self.project.pulumi_config.require_secret('cloudflare_zone_id')
    return {
        service: cloudflare.DnsRecord(
            f'{self.name}-priv-{service}-dns',
            name=f'{self.project.name_prefix}-{service}-i',
            ttl=60,
            type='CNAME',
            zone_id=cloudflare_zone_id,
            content=private_lbs[service].resources['load_balancer'].dns_name,
            proxied=False,
        )
        for service, lb in private_lbs.items()
    }