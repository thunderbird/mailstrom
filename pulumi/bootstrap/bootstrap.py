#!/bin/env python3.12

import boto3
import json
import logging
import requests
from jinja2 import Environment, FileSystemLoader
from traceback import print_exc

BOOTSTRAP_DIR = '/opt/stalwart-bootstrap'
BOOTSTRAP_LOG = '/var/log/stalwart-bootstrap.log'
INSTANCE_TAGS = {}
# Map of template files to target files
TEMPLATE_MAP = {
    'stalwart.toml.j2': '/opt/stalwart-mail/etc/config.toml',
    'thundermail.service.j2': '/usr/lib/systemd/system/thundermail.service',
}
# Map of template variable to EC2 tags
TEMPLATE_VALUE_TAG_MAP = {
    'node_services': 'postboot.stalwart.node_services',
    'node_id': 'postboot.stalwart.node_id',
    'node_roles': 'postboot.stalwart.node_roles',
}

log_format = '[%(asctime)s] %(levelname)s - %(message)s'
logging.basicConfig(filename=BOOTSTRAP_LOG, level=logging.INFO, format=log_format)
log = logging.getLogger(__name__)


def get_instance_tags() -> dict:
    # Get an auth token
    auth_response = requests.put(
        'http://169.254.169.254/latest/api/token',
        headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'},
    )
    if auth_response.status_code != 200:
        raise RuntimeError(
            'Failed to authenticate against instance metadata service. Response: '
            f'{auth_response.status_code} {auth_response.reason}'
        )
    auth_token = auth_response.text

    # Get the instance tags
    taglist_response = requests.get(
        'http://169.254.169.254/latest/meta-data/tags/instance', headers={'X-aws-ec2-metadata-token': auth_token}
    )
    if taglist_response.status_code != 200:
        raise RuntimeError(
            'Failed to retrieve a list of instance tags. Response: '
            f'{taglist_response.status_code} {taglist_response.reason}'
        )
    tag_keys = taglist_response.text.split()

    # Compile and return the tags
    tags = {}
    for key in tag_keys:
        tag_response = requests.get(
            f'http://169.254.169.254/latest/meta-data/tags/instance/{key}',
            headers={'X-aws-ec2-metadata-token': auth_token},
        )
        if tag_response.status_code != 200:
            log.error(f'Failed to retrieve the value for tag "{key}"')
        tags[key] = tag_response.text

    log.info(f'Retrieved instance tags: {tags}')

    return tags


def get_secrets(env: str, aws_region: str) -> dict:
    # Map of template vars to SM secrets
    secret_value_map = {
        'fallback_admin_password': f'mailstrom/{env}/stalwart.postboot.fallback_admin_password',
        'jmap_toml': f'mailstrom/{env}/stalwart.postboot.jmap_toml',
        'postgresql_backend': f'mailstrom/{env}/stalwart.postboot.postgresql_backend',
        'redis_backend': f'mailstrom/{env}/stalwart.postboot.redis_backend',
        's3_iam_access_key': f'mailstrom/{env}/iam.user.mailstrom-{env}-stalwart.access_key',
        's3_backend': f'mailstrom/{env}/stalwart.postboot.s3_backend',
        'tb_accounts_backend': f'mailstrom/{env}/stalwart.postboot.tb-accounts_backend',
    }
    sm_client = boto3.client('secretsmanager', region_name=aws_region)

    secrets = {}
    for template_key, secret_id in secret_value_map.items():
        try:
            secret = sm_client.get_secret_value(SecretId=secret_id)
            try:
                secret_value = secret['SecretString']
                secrets[template_key] = json.loads(secret_value)
            except Exception:
                secrets[template_key] = secret['SecretString']
        except Exception as ex:
            log.error(print_exc(ex))
            secrets[template_key] = None
    return secrets


def render_templates(template_values: dict) -> None:
    j2_dir = f'{BOOTSTRAP_DIR}/templates'
    j2_loader = FileSystemLoader(j2_dir)
    j2_env = Environment(loader=j2_loader)

    for source_file, target_file in TEMPLATE_MAP.items():
        rendered_template = j2_env.get_template(source_file).render(**template_values)
        with open(target_file, 'w') as fh:
            log.info(f'Writing {target_file} to disk...')
            fh.write(rendered_template)


def main():
    log.info('Bootstrapping begins now...')

    global INSTANCE_TAGS
    INSTANCE_TAGS = get_instance_tags()
    template_values = {template_key: INSTANCE_TAGS[tag_key] for template_key, tag_key in TEMPLATE_VALUE_TAG_MAP.items()}

    for template_key, secret_value in get_secrets(
        env=INSTANCE_TAGS['postboot.stalwart.env'], aws_region=INSTANCE_TAGS['postboot.stalwart.aws_region']
    ).items():
        template_values[template_key] = secret_value

    render_templates(template_values=template_values)

    log.info('Bootstrapping complete!')


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        log.error(print_exc(ex))
