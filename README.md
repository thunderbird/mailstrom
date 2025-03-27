# Thunderbird Pro Mail Service

This project aims to deploy Stalwart Mail Server in a scalable way using Pulumi and
[tb_pulumi](https://github.com/thunderbird/pulumi/).

Some terminology for clarity:

- **Thundermail:** The marketing name of an email service provided by Thunderbird.
- **Mailstrom:** The name of the infrastructure-as-code project which builds/manages Thundermail's infrastructure.
- **Stalwart:** An open source email platform ([stalw.art](https://stalw.art/)) deployed by Mailstrom.
- **Pulumi:** An infrastructure-as-code library and platform ([pulumi.com](https://www.pulumi.com/)).
- **tb_pulumi:** An extension of Pulumi defining some common infrastructure patterns at Thunderbird.


## How Stalwart Node Bootstrapping Works

In the broadest strokes:

- The `bootstrap` directory contains a script and related files that will eventually run on a Stalwart node at launch
  time.
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

This project follows the conventions outlined in
[tb_pulumi documentation](https://thunderbird.github.io/pulumi/patterns.html#patterns-for-managing-projects). The
Stalwart cluster is declared in the `pulumi/__main__.py` file, but the configuration for that resource is mostly
contained in the `config.$env.yaml` file. Begin with this config shell:

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
          #     - your-jumphosts-id-maybe
```

Adjust these values to your liking, adding additional nodes as needed.

### Database Config

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

Ensure that secret is pushed to AWS by the `PulumiSecretsManager`:

```yaml
resources:
  # ...
  tb:secrets:PulumiSecretsManager:
    secrets:
      secret_names:
        - stalwart.postboot.postgresql_backend
```

This ensures the secret is populated with your connection details at the time the instances bootstrap and retrieve it.

The Redis and S3 storage backends are created by this module. Their connection details are stored in secrets
automatically by the `StalwartCluster` module.


## Debugging

### SSH Setup

You may need to gain SSH access to the Stalwart nodes to debug problems. The nodes are all built in private network
space with no external access, though, which prevents this. To get around this, you will need to build an SSH bastion —
a server that exposes private SSH connections through a single public interface — by adding a
`tb_pulumi.ec2.SshableInstance` to the project in `pulumi/__main__.py`.

```python
tb_pulumi.ec2.SshableInstance(
    f'{project.name_prefix}-{jumphost}',
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
group. You should now be able to SSH directly into the node, punching into the private network via the bastion.

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

### Bootstrapping

The bootstrapping process begins at the instance's user data. This contains a base64-encoded zip file embedded as a
string in a Bash script. The user data script unpacks this into `/opt/stalwart-bootstrap`. It then builds a Python
virtual environment and installs dependencies for the second stage. The output from this script can be found among other
startup logs in `/var/log/cloud-init-output.log`.

The content of the user data script can be gathered from the AWS EC2 web console.

- Locate your instance and right-click it.
- Click "Instance settings"
- Click "Edit user data"

**Note:** You cannot change the user data without stopping the instance. You obviously do not want to do this with any
instance that is running an essential service. The `ignore_user_data_changes` option prevents accidental restarting of
nodes in the `StalwartCluster` due to changes in automatically generated user data.

The Bash script will then run the second stage Python script. This gathers instance tag data from the internal instance
[metadata service](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/work-with-tags-in-IMDS.html) and secret info like
database credentials from AWS Secrets Manager. It compiles this data into a mapping of template variables to their
values and feeds that into the templates for rendering.


### Re-Running Bootstrapping

The user data script is not available as a file on the system to run, but you can copy and paste it out of the web
console if you need to do that.

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


### Logs

You can access the logs from the current Stalwart session with Docker:

```bash
docker logs stalwart-mail
```

You can access historical logs from the current and previous Stalwart sessions with the system journal:

```bash
journalctl -fu thundermail | less
```
