# Thunderbird Pro Mail Service Infrastructure Documentation

This project aims to deploy [Stalwart Mail Server](https://stalw.art/) in a scalable way using
[Pulumi](https://www.pulumi.com/) and [tb_pulumi](https://github.com/thunderbird/pulumi/).

Some terminology for clarity:

- **Thundermail:** The marketing name of an email service provided by Thunderbird.
- **Mailstrom:** The name of the infrastructure-as-code project which builds/manages Thundermail's infrastructure.
- **Stalwart:** An open source email platform deployed by Mailstrom.
- **Pulumi:** An infrastructure-as-code library and platform.
- **tb_pulumi:** An extension of Pulumi defining some common infrastructure patterns at Thunderbird.


## How Stalwart Node Bootstrapping Works

In the broadest strokes:

- The `bootstrap` directory contains a script and related files that will eventually run on a Stalwart node at launch
  time to configure a running Stalwart instance there.
- The `stalwart.StalwartCluster` class zips up these bootstrapping files, base64-encodes the zip, and injects that
  string into a Bash script template (stalwart_instance_user_data.sh.j2).
- That script gets set as the instance's user data script, such that when the instance is first launched, the script
  runs.
- Additional configuration is stored either as tags on the instance or as secrets (credentials, etc.)
- The first bootstrap stage unpacks the stage-two zip file and runs the Python script contained therein.
- The second stage script templates a config file for Stalwart and a systemd service file that runs it as a docker
  container when the instance comes online.

In this way, a `pulumi up` with a proper node configuration can bootstrap a functioning Stalwart cluster.


## Configuration

### YAML Config

This project follows the conventions outlined in the
[tb_pulumi documentation](https://thunderbird.github.io/pulumi/patterns.html#patterns-for-managing-projects). All code
related to infrastructure lives in the `pulumi/` directory. The Stalwart cluster is declared in the `__main__.py` file,
but the configuration for that resource is mostly contained in the `config.$env.yaml` file. Begin with this config
shell:

```yaml
resources:
  tb:mailstrom:StalwartCluster:
    thundermail:
      nodes:
        "0": # Entries in this list must be stringified integers; this will become the Stalwart cluster node-id.
          disable_api_termination: False # Set to True in production environments; prevent accidental deletion of nodes
          ignore_ami_changes: True # Prevent the node from being rebuilt when AWS releases a new OS
          ignore_user_data_changes: True # Prevent the node from restarting when user data changes
          instance_type: t3.micro
          key_name: your-ec2-keypair # Keypair to use for SSH access
          node_roles: # Stalwart cluster node roles to enable (not really implemented yet)
            - all
          services: # List of services to enable on the node, or "all"
            - all # Enable all services; incompatible with other services
            # - http
            # - imap
            # - imaps
            # - lmtp
            # - managesieve
            # - pop3
            # - pop3s
            # - smtp
            # - smtps
          storage_capacity: 20 # Ephemeral storage volume size in GB
      load_balancer:
        services: # Configuration of service exposure through the load balancer
          http: # "http" is the web admin interface, which should never be exposed to the world; restrict the sources.
            source_cidrs: ['10.1.0.0/16']
          imap: # Actual mail services should be public, though
            source_cidrs: ['0.0.0.0/0']
          imaps:
            source_cidrs: ['0.0.0.0/0']
          lmtp:
            source_cidrs: ['0.0.0.0/0']
          managesieve:
            source_cidrs: ['0.0.0.0/0']
          smtp:
            source_cidrs: ['0.0.0.0/0']
          smtps:
            source_cidrs: ['0.0.0.0/0']
          # The "all" service exposes all services to the same set of sources. If you do this, you should only ever
          # expose them to private network space for testing purposes. Exposing "all" to the world exposes the web admin
          # interface to the world, which you should never do.
          # all: 
          #   source_cidrs:
          #     - 10.1.0.0/16
          #   source_security_group_ids:
          #     - your-ssh-bastions-id-maybe
```

Adjust these values to your liking, adding additional nodes as needed.

### Additional Secrets

This project uses [Neon Databases](https://neon.tech/) as a Postgres backend. There is currently no Neon provider in the
Pulumi registry, so this resource is managed manually. The details of the database connection must nevertheless be
delivered to the EC2 instances, so you must store this data in AWS Secrets Manager. If you would prefer to use some
other Postgres compatible storage backend like RDS, you may do so and specify the connection details in this secret.

Craft the data:

```json
{
  "host": "database-hostname",
  "port": 5432,
  "database": "db_name",
  "user": "db_user",
  "password": "db_password",
  "tls": {
    "enable": true,
    "allow-invalid-certs": false
  }
}
```

Paste that into a config command:

```sh
pulumi config set --secret stalwart.postboot.postgresql_backend '$all_that_json'
```

You'll also need to set the web admin panel's password by setting `stalwart.postboot.fallback_admin_password` to some
secure string.

Ensure these secrets are pushed to AWS by the `PulumiSecretsManager`:

```yaml
resources:
  # ...
  tb:secrets:PulumiSecretsManager:
    secrets:
      secret_names:
        - stalwart.postboot.fallback_admin_password
        - stalwart.postboot.postgresql_backend
```

This ensures the secrets are populated with your connection details at the time the instances bootstrap and retrieve
them.

**Note:** The Redis and S3 storage backends are created by this module. Their connection details are stored in secrets
automatically by the `StalwartCluster` module; you need take no additional action regarding those stores.


## Debugging

### SSH Setup

You may need to gain SSH access to the Stalwart nodes to debug problems. The nodes are all built in private network
space with no external access, though, which prevents this. To get around this, you will need to build an SSH bastion —
a server that exposes private SSH connections through a single public interface — by adding a
`tb_pulumi.ec2.SshableInstance` to the project in `__main__.py`.

```python
tb_pulumi.ec2.SshableInstance(
    f'{project.name_prefix}-bastion',
    project=project,
    subnet_id=vpc.resources['subnets'][0].id,
    vpc_id=vpc.resources['vpc'].id,
    public_key='your_ssh_public_key_here',
    source_cidrs=['$your_public_ip_address/32'],
    opts=pulumi.ResourceOptions(depends_on=[vpc]),
)
```

SSH into that machine and install your `id_rsa` and `id_rsa.pub` files into `/home/ec2-user/.ssh/`. Set appropriate file
permissions.

```bash
chmod 0600 /home/ec2-user/.ssh/id_rsa*
```

On your local machine, edit your `~/.ssh/config` file to include these sections:

```
Host mailstrom-my-bastion
    Hostname $bastion_public_ip
    User ec2-user

# Adjust this IP range to match the actual network
Host 10.1.*
    User ec2-user
    ProxyCommand ssh -W %h:%p mailstrom-my-bastion
```

In AWS, add a rule to the Stalwart node's security group allowing SSH (22/tcp) access from your bastion's security
group. You should now be able to SSH directly into the node, punching through to the private network via the bastion.

```
# ssh $node_ip
The authenticity of host '$node_id ($node_id) can't be established.
ED25519 key fingerprint is SHA256:somethingugly.
This key is not known by any other names.
Are you sure you want to continue connecting (yes/no/[fingerprint])? yes
```

### Accessing the Web Admin Panel

If you have the above SSH configuration working, you should also be able to open an SSH tunnel into the privately
operating web admin panel.

**Warning!** You should not expose your Stalwart admin web interface to any public network. Configure the node whose
admin panel you want to access to enable the `http` service (implicit in the `all` service):

```yaml
nodes:
  "0":
    # ...various settings here...
    services:
      - http
      # - all
```

There is no need to expose this service through the load balancer. Instead, establish an SSH tunnel to the service:

```bash
ssh -L 8080:$node_ip:8080 $node_ip
```

Now you have access to the admin panel by pointing a browser on your local machine to http://localhost:8080/

### Bootstrapping a Stalwart Node

A Stalwart node is an EC2 instance running Stalwart Mail as a Docker service. It runs Amazon Linux 2023 as an operating
system. The bootstrapping process begins as instance user data. This contains a base64-encoded zip file embedded as a
string in a Bash script. The user data script unpacks this into `/opt/stalwart-bootstrap`. It then builds a Python
virtual environment and installs dependencies for the second stage. The output from this script can be found among other
startup logs in `/var/log/cloud-init-output.log`.

The Bash script will then run the second stage Python script. This gathers instance tag data from the internal instance
[metadata service](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/work-with-tags-in-IMDS.html) and secret info like
database credentials from AWS Secrets Manager. It compiles this data into a mapping of template variables to their
values and feeds that into the templates for rendering.

**Note:** You cannot change the user data without stopping the instance. You obviously do not want to do this with any
instance that is running an essential service. The `ignore_user_data_changes` option to a node's configuration prevents
accidental restarting of nodes in the `StalwartCluster` due to changes in automatically generated user data. It is
strongly recommended to keep this set to `True` anytime you are not deliberately performing maintenance.

**Another Note:** This user data *only* runs on the first launch of an instance. It *does not* run on subsequent reboots
or instance stop/starts. If you want to re-run the bootstrapping process as a means of updating the server's config, you
will need to manually re-run the bootstrapping process. This is described below.

**And One More Note:** We use tb_pulumi's
[`get_latest_amazon_linux_ami`](https://thunderbird.github.io/pulumi/tb_pulumi.html#tb_pulumi.ThunderbirdPulumiProject.get_latest_amazon_linux_ami)
function to get the most recent Amazon Linux 2023 image. This will change automatically whenever AWS releases a new AMI.
An instance cannot simply change its AMI; you must destroy it and replace the whole server. This is another thing you
don't want to do to an essential server. To prevent this, it is strongly recommended that you set `ignore_ami_changes`
to `True` on each node.


### Re-Running Bootstrapping

The user data script is not available as a file on the system to run, but you can copy and paste it out of the web
console if you need to do that:

1. Locate your instance and right-click it.
2. Click "Instance settings"
3. Click "Edit user data"


To re-run the second phase, activate the bootstrap virtual environment and run the script:

```bash
cd /opt/stalwart-bootstrap
source bin/activate
python bootstrap.py
```

This outputs its logs to `/var/log/stalwart-bootstrap.log`. If you are iterating repeatedly, it may help to use this
command to keep your output fresh with every run:

```bash
> /var/log/stalwart-bootstrap.log; python bootstrap.py & tail -f /var/log/stalwart-bootstrap.log
```

A typical run will look something like this (except with prepended timestamps, which have been removed for readability,
and your instance's actual tags and configuration listed):

```
INFO - Bootstrapping begins now...
INFO - Retrieved instance tags: {'Name': 'mailstrom-yourstack-stalwart-1', 'environment': 'yourstack', 'postboot.stalwart.aws_region': 'eu-central-1', 'postboot.stalwart.env': 'yourstack', 'postboot.stalwart.node_id': '1', 'postboot.stalwart.node_roles': 'acme_renew,metrics_calculate,metrics_push,purge_accounts,purge_stores', 'postboot.stalwart.node_services': 'imap,imaps,lmtp,managesieve,pop3,pop3s,smtp,smtps', 'project': 'mailstrom', 'pulumi_last_run_by': 'yourstack@yourmachine', 'pulumi_project': 'mailstrom', 'pulumi_stack': 'yourstack'}
INFO - Found credentials from IAM Role: mailstrom-yourstack-stalwart-stalwart-node-profile
INFO - Writing /opt/stalwart-mail/etc/config.toml to disk...
INFO - Writing /usr/lib/systemd/system/thundermail.service to disk...
INFO - Bootstrapping complete!
```


### The Templated Files

There are currently two files of note on each node:

- `/opt/stalwart-mail/etc/config.toml` - This is the Stalwart config. It contains only those settings that are required
  to be stored on the local machine. This includes the configuration to the database where it can find all the rest of
  the settings.
- `/usr/lib/systemd/system/thundermail.service` - This configures Stalwart as a monitored systemd service using the
  [Docker installation method](https://stalw.art/docs/install/docker/).

To affect a change in Stalwart, you can edit the `config.toml` file and restart the `thundermail` service:

```bash
systemctl restart thundermail
```

You can check the status and aliveness of the service:

```bash
systemctl status thundermail
```

Manage the state of the service:

```bash
systemctl start/stop/restart thundermail
```

If the service is running, you should also be able to see the container with `docker ps`.


### Logs and Docker Stuff

You can access the logs from the current Stalwart session with Docker:

```bash
docker logs stalwart-mail
```

You can access historical logs from the current and previous Stalwart sessions with the system journal:

```bash
journalctl -fu thundermail | less
```

If you want to run the container in the foreground, you can run the Docker command found in the service file. Because
nodes can be configured to run different sets of services, this command may be different on different nodes. It will
look something like this:

```bash
docker run --rm --name stalwart-mail \ # Name this container, delete stopped containers of the same name before running
  -v /opt/stalwart-mail:/opt/stalwart-mail \ # Mount /opt/stalwart-mail on the host machine into the container
  -p 8080:8080 \ # List of ports to expose on the host
  -p 143:143 \   # One for each service
  -p 993:993 \
  -p 25:25 \
  -p 587:587 \
  # -p etc:etc \
  stalwartlabs/mail-server:v0.11 # Use the latest revision of v0.11
```

If you want to run the container in the foreground *with an interactive shell prompt* you must additionally override the
entrypoint and set up an interactive TTY:

```bash
docker run \ # ...other options...
  -it --entrypoint bash \
  # ...other options...
  stalwartlabs/mail-server:v0.11
```