"""Guards that stalwart.toml.j2 only uses variables the bootstrap actually supplies.

The JMAP block was gated on `{% if jmap %}` while bootstrap.py only ever defines
`jmap_toml`. Jinja renders an undefined name as falsy without raising, so the whole
block was silently dropped from every node's config.toml and Stalwart ran on its
compiled-in JMAP defaults instead.
"""

import ast
from pathlib import Path

import pytest
import toml
import yaml
from jinja2 import Environment, FileSystemLoader, nodes
from jinja2.meta import find_undeclared_variables

REPO = Path(__file__).resolve().parents[2]
TEMPLATES = REPO / 'pulumi/bootstrap/templates'
BOOTSTRAP = REPO / 'pulumi/bootstrap/bootstrap.py'
TEMPLATE = 'stalwart.toml.j2'

# `spam_filter` guards `spam_filter_toml` and has exactly the same defect the jmap gate
# had. Correcting it activates a spam-filter config that has never run in production, so
# it needs reviewing on its own rather than riding along with an unrelated change.
KNOWN_UNDEFINED = {'spam_filter'}

# Stand-ins for the secret payloads, only detailed enough for the template to render.
STUB_SECRETS = {
    'keycloak_backend': {
        'auth_method': 'basic',
        'auth_username': 'u',
        'auth_secret': 's',
        'endpoint_method': 'introspect',
        'endpoint_url': 'https://example.test/introspect',
        'fields_email': 'username',
        'timeout': '15s',
    },
    'postgresql_backend': {'host': 'db.test', 'database': 'stalwart', 'user': 'u', 'password': 'p'},
    's3_backend': {'bucket': 'b', 'region': 'eu-central-1'},
    'redis_backend': {'timeout': '15s'},
}
STUB_TAGS = {
    'node_id': 10,
    'node_services': 'https,imaps,lmtp,managesieve,smtp,smtps,submission',
    'node_roles': 'all',
    'https_paths': '/jmap,/.well-known/jmap',
    'stalwart_image': 'stalwartlabs/stalwart:v0.15.4',
}


def _declaration(name: str):
    """Read a literal assignment out of bootstrap.py.

    It cannot be imported: at module scope it points logging.basicConfig at
    /var/log/stalwart-bootstrap.log, which is not writable off a node.
    """
    tree = ast.parse(BOOTSTRAP.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise AssertionError(f'no literal assignment to {name} in {BOOTSTRAP}')


@pytest.fixture(scope='module')
def provided() -> set[str]:
    """Every name bootstrap.py puts into the Jinja context."""
    return set(_declaration('TEMPLATE_VALUE_TAG_MAP')) | set(_declaration('secret_names'))


@pytest.fixture(scope='module')
def env() -> Environment:
    return Environment(loader=FileSystemLoader(TEMPLATES))


def test_template_only_references_variables_bootstrap_provides(env, provided):
    source = (TEMPLATES / TEMPLATE).read_text()
    # Names the template sets itself, plus those inherited from ports.j2 via extends.
    local = {
        assign.target.name
        for path in TEMPLATES.iterdir()
        for assign in env.parse(path.read_text()).find_all(nodes.Assign)
    }

    missing = find_undeclared_variables(env.parse(source)) - provided - local

    assert missing == KNOWN_UNDEFINED, (
        f'{TEMPLATE} references {sorted(missing)}; bootstrap.py defines {sorted(provided)}. '
        f'Jinja treats an undefined name as falsy/empty instead of failing, so any config it '
        f'guards is silently dropped. Add the variable to bootstrap.py or correct the '
        f'reference -- and if you fixed one of {sorted(KNOWN_UNDEFINED)}, drop it from '
        f'KNOWN_UNDEFINED.'
    )


@pytest.mark.parametrize('stack', ['prod', 'stage', 'dev'])
def test_jmap_config_reaches_the_rendered_config_toml(env, provided, stack):
    cluster = yaml.safe_load((REPO / f'pulumi/config.{stack}.yaml').read_text())
    jmap = next(iter(cluster['resources']['tb:mailstrom:StalwartCluster'].values()))['jmap']

    context = {name: '' for name in provided} | STUB_TAGS | STUB_SECRETS
    # Built exactly as the Pulumi program builds the secret it stores for the nodes.
    context['jmap_toml'] = toml.dumps({'jmap': jmap})

    rendered = env.get_template(TEMPLATE).render(**context)

    assert '[jmap.protocol.upload.quota]' in rendered, (
        f'the {stack} jmap config never reached config.toml; Stalwart would fall back to '
        f'its built-in defaults, including a 1000 file / 50 MB hourly blob upload quota'
    )
