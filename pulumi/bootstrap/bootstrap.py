#!/bin/env python3.12

"""This is a second stage bootstrapping script designed to template some configuration files into place based on a
configuration made available through EC2 instance tags and Secrets Manager secrets.
"""

import boto3
import json
import logging
import requests

from jinja2 import Environment, FileSystemLoader
from traceback import print_exc

# Location where the bootstrapping data can be found
BOOTSTRAP_DIR = '/opt/stalwart-bootstrap'
# Location where this script should output its logs
BOOTSTRAP_LOG = '/var/log/stalwart-bootstrap.log'
# Dict of tags on this instance
INSTANCE_TAGS = {}
# Mapping where keys are source templates and values are target filenames for the rendered output
TEMPLATE_MAP = {
    'stalwart.toml.j2': '/opt/stalwart-mail/etc/config.toml',
    'thundermail.service.j2': '/usr/lib/systemd/system/thundermail.service',
}
# Mapping where keys are variables as they are known to our templates and values are the names of the EC2 tags whose
# values should populate the template variables.
TEMPLATE_VALUE_TAG_MAP = {
    'node_services': 'postboot.stalwart.node_services',
    'node_id': 'postboot.stalwart.node_id',
    'node_roles': 'postboot.stalwart.node_roles',
}

# Set up logging
log_format = '[%(asctime)s] %(levelname)s - %(message)s'
logging.basicConfig(filename=BOOTSTRAP_LOG, level=logging.INFO, format=log_format)
log = logging.getLogger(__name__)


def get_instance_tags() -> dict:
    """Retrieves the instance tags for the instance this script is running on. Requires that the instance tags be made
    available through the instance metadata service. Ref:
    https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/work-with-tags-in-IMDS.html
    """

    # The instance metadata service is authenticated. Get a token.
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

    # Now get a list of instance tags; this response is unfancy plaintext, one tag per line
    taglist_response = requests.get(
        'http://169.254.169.254/latest/meta-data/tags/instance', headers={'X-aws-ec2-metadata-token': auth_token}
    )
    if taglist_response.status_code != 200:
        raise RuntimeError(
            'Failed to retrieve a list of instance tags. Response: '
            f'{taglist_response.status_code} {taglist_response.reason}'
        )
    tag_keys = taglist_response.text.split()

    # Finally, get the value of each tag, compiling them into one dict to be returned
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
    """Retrieves the secret values required to bootstrap the Stalwart node. Automatically converts JSON-parsable values
    into Python dicts because doing that in Jinja is uglier and harder to debug. Invalid secret IDs will get a ``None``
    value.

    :param env: Environment to get secrets from
    :type env: str

    :param aws_region: Name of the AWS region the env operates in.
    :type aws_region: str

    :return: Mapping of template variable names to the secret values they represent.
    :rtype: dict
    """

    # Mapping where the keys are variable names found in our templates and the values are the IDs of the secrets
    # containing the secret values.
    secret_value_map = {
        'postgresql_backend': f'mailstrom/{env}/stalwart.postboot.postgresql_backend',
        'redis_backend': f'mailstrom/{env}/stalwart.postboot.redis_backend',
        's3_iam_access_key': f'mailstrom/{env}/iam.user.mailstrom-{env}-stalwart.access_key',
        's3_backend': f'mailstrom/{env}/stalwart.postboot.s3_backend',
    }
    sm_client = boto3.client('secretsmanager', region_name=aws_region)
    
    # Build and return a new mapping with the same keys, but the values are the actual secret values
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
    """Renders all templates in the TEMPLATE_MAP to their target files, populating variables with the provided
    template_values.

    :param template_values: Mapping of values to populate the template variables with.
    :type template_values: dict
    """

    # Build a Jinja rendering environment so the "extends" expressions will work
    j2_dir = f'{BOOTSTRAP_DIR}/templates'
    j2_loader = FileSystemLoader(j2_dir)
    j2_env = Environment(loader=j2_loader)

    # Render each template into place on disk
    for source_file, target_file in TEMPLATE_MAP.items():
        rendered_template = j2_env.get_template(source_file).render(**template_values)
        with open(target_file, 'w') as fh:
            log.info(f'Writing {target_file} to disk...')
            fh.write(rendered_template)


def main():
    """Main entry point."""

    log.info('Bootstrapping begins now...')

    # Map instance tags into template values based on our TEMPLATE_VALUE_TAG_MAP
    global INSTANCE_TAGS
    INSTANCE_TAGS = get_instance_tags()
    template_values = {template_key: INSTANCE_TAGS[tag_key] for template_key, tag_key in TEMPLATE_VALUE_TAG_MAP.items()}

    # Add secret values to the mapping
    for template_key, secret_value in get_secrets(
        env=INSTANCE_TAGS['postboot.stalwart.env'], aws_region=INSTANCE_TAGS['postboot.stalwart.aws_region']
    ).items():
        template_values[template_key] = secret_value

    # Render all of the templates to disk
    render_templates(template_values=template_values)

    log.info('Bootstrapping complete!')


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        # When things fail, always output the traceback into the log file so it can be debugged
        log.error(print_exc(ex))
