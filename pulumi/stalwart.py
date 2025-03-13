"""Infrastructural patterns related to `Stalwart Mail Server <https://stalw.art/docs/get-started/>`_"""

import base64
import pulumi
import pulumi_aws as aws
import tb_pulumi
import tb_pulumi.network

from enum import Enum
from jinja2 import Template
from zipfile import ZipFile


#: Mapping of supported cluster services and their associated ports
STALWART_CLUSTER_SERVICES = {
    "all": None,
    "http": 8080,
    "imap": 143,
    "imaps": 993,
    "lmtp": 24,
    "managesieve": 4190,
    "pop3": 110,
    "pop3s": 995,
    "smtp": 25,
    "smtps": 587,
}


class StalwartNodeRoles(Enum):
    """Discrete set of supported Stalwart cluster node roles."""

    ALL = 0
    ACME_RENEW = 1
    METRICS_CALCULATE = 2
    METRICS_PUSH = 3
    PURGE_ACCOUNTS = 4
    PURGE_STORES = 5


class StalwartCluster(tb_pulumi.ThunderbirdComponentResource):
    """**Pulumi Type:** ``tb:accounts:StalwartCluster``

    Builds EC2 instances which operate as a Stalwart Mail Server cluster.

    Produces the following ``resources``:

        - *whatever* - Something
    """

    def __init__(
        self,
        name: str,
        project: tb_pulumi.ThunderbirdPulumiProject,
        subnets: list[aws.ec2.Subnet],
        cluster_services: dict = {},
        nodes: dict = {},
        exclude_from_project: bool = False,
        opts: pulumi.ResourceOptions = None,
        tags: dict = {},
        **kwargs,
    ):
        super().__init__(
            "tb:accounts:StalwartCluster",
            name=name,
            project=project,
            opts=opts,
            tags=tags,
        )

        # Sanity check some inputs
        if len(subnets) == 0:
            raise ValueError("You must provide at least one subnet.")
        if len(cluster_services) > 1 and "all" in cluster_services:
            raise ValueError(
                'If the "all" cluster service is set for a node, no other services may be set.'
            )

        __handle_all_services = (
            True if len(cluster_services) == 1 and "all" in cluster_services else False
        )

        # All subnets must be in the same VPC. For convenience, we grab the ID from the first subnet.
        vpc_id = subnets[0].vpc_id

        # First build the security group we will use on our load balancer
        lb_sg_rules = {
            "egress": [
                {
                    "description": "Allow traffic outbound from the load balancer",
                    "protocol": "tcp",
                    "from_port": 0,
                    "to_port": 65535,
                    "cidr_blocks": ["0.0.0.0/0"],
                }
            ],
            "ingress": [],
        }

        # Build a list of security group rules for the load balancer based on the config
        if __handle_all_services:
            __cluster_services = STALWART_CLUSTER_SERVICES.copy()
            del (__cluster_services)["all"]
        else:
            __cluster_services = cluster_services

        for service in __cluster_services:
            if service not in STALWART_CLUSTER_SERVICES:
                raise ValueError(f"{service} is not a valid Stalwart cluster service.")

            if __handle_all_services:
                __service_config = cluster_services["all"]
            else:
                __service_config = cluster_services[service]

            if "source_cidrs" in __service_config:
                lb_sg_rules["ingress"].append(
                    {
                        "description": f"Allow {service} traffic by IP",
                        "protocol": "tcp",
                        "from_port": STALWART_CLUSTER_SERVICES[service],
                        "to_port": STALWART_CLUSTER_SERVICES[service],
                        "cidr_blocks": __service_config["source_cidrs"],
                    }
                )
            if "source_security_group_ids" in __service_config:
                for sgid in __cluster_services[service]["source_security_group_ids"]:
                    lb_sg_rules["ingress"].append(
                        {
                            "description": f"Allow {service} traffic from {sgid}",
                            "protocol": "tcp",
                            "from_port": STALWART_CLUSTER_SERVICES[service],
                            "to_port": STALWART_CLUSTER_SERVICES[service],
                            "source_security_group_id": sgid,
                        }
                    )

        lb_sg = tb_pulumi.network.SecurityGroupWithRules(
            name=f"{name}-lbsg",
            project=project,
            rules=lb_sg_rules,
            vpc_id=vpc_id,
            opts=pulumi.ResourceOptions(parent=self),
            tags=self.tags,
        )

        instances = {}
        for idx, node_id in enumerate(nodes):
            instances[node_id] = StalwartClusterNode(
                name=f"{name}-{node_id}",
                project=project,
                load_balancer_security_group_id=lb_sg.resources["sg"].id,
                node_id=node_id,
                subnet=subnets[idx % len(subnets)],
                opts=opts,
                tags=tags,
                exclude_from_project=True,
                **nodes[node_id],
                **kwargs,
            )

        self.finish(resources={"lb_sg": lb_sg, "instances": instances})


class StalwartClusterNode(tb_pulumi.ThunderbirdComponentResource):
    """**Pulumi Type:** ``tb:accounts:StalwartClusterNode``

    Builds an EC2 instance and a security group setup for a single cluster instance's needs.

    Produces the following ``resources``:

        - *whatever* - Something

    :param exclude_from_project: When ``True`` , this prevents this component resource from being registered directly
        with the project. This does not prevent the component resource from being discovered by the project's
        ``flatten`` function, provided that it is nested within some resource that is not excluded from the project.
    :type exclude_from_project: bool, optional

    """

    def __init__(
        self,
        name: str,
        project: tb_pulumi.ThunderbirdPulumiProject,
        load_balancer_security_group_id: str,
        node_id: str,
        subnet: str,
        cluster_services: list[str] = ["all"],
        disable_api_stop: bool = False,
        disable_api_termination: bool = False,
        ignore_ami_changes: bool = True,
        ignore_user_data_changes: bool = True,
        instance_type: str = "t2.micro",
        storage_capacity: int = 20,
        node_roles: list[str] = ["all"],
        user_data_archive: str = "bootstrap.zip",
        user_data_template: str = "stalwart_instance_user_data.sh.j2",
        exclude_from_project: bool = False,
        opts: pulumi.ResourceOptions = None,
        tags: dict = {},
        **kwargs,
    ):
        super().__init__(
            "tb:accounts:StalwartClusterNode",
            name=name,
            project=project,
            opts=opts,
            tags=tags,
        )

        # Sanity check the node role values
        if len(node_roles) > 1 and "all" in node_roles:
            raise ValueError(
                'If the "all" node role is set for a node, no other roles may be set.'
            )
        for role in node_roles:
            if role.upper() not in StalwartNodeRoles.__members__.keys():
                raise ValueError(f'"{role}" is not a valid node role.')

        # Sanity check the node service values
        if len(cluster_services) > 1 and "all" in cluster_services:
            raise ValueError(
                'If the "all" node service is set for a node, no other services may be set.'
            )
        for service in cluster_services:
            if service.lower() not in STALWART_CLUSTER_SERVICES.keys():
                raise ValueError(f'"{service}" is not a valid node service.')

        __handle_all_services = (
            True if len(cluster_services) == 1 and "all" in cluster_services else False
        )

        # Build an instance-dedicated security group with rules specific to the services available on the machine
        sg_rules = {
            "egress": [
                {
                    "description": "Allow traffic from the instance out to the Internet",
                    "protocol": "tcp",
                    "from_port": 0,
                    "to_port": 65535,
                    "cidr_blocks": ["0.0.0.0/0"],
                }
            ],
            "ingress": [],
        }

        if __handle_all_services:
            # Build for all services except the special "all" service
            __cluster_services = STALWART_CLUSTER_SERVICES.copy()
            del __cluster_services["all"]
        else:
            # Build for whatever more specific services the user supplied
            __cluster_services = cluster_services

        # Instances only ever receive traffic from load balancers
        for service in __cluster_services:
            sg_rules["ingress"].append(
                {
                    "description": f"Allow {service} traffic",
                    "protocol": "tcp",
                    "from_port": STALWART_CLUSTER_SERVICES[service],
                    "to_port": STALWART_CLUSTER_SERVICES[service],
                    "source_security_group_id": load_balancer_security_group_id,
                }
            )

        sg = tb_pulumi.network.SecurityGroupWithRules(
            name=f"{name}-sg",
            project=project,
            rules=sg_rules,
            vpc_id=subnet.vpc_id,
        )

        # Tags for the instance that inform behavior in the postboot playbook
        postboot_tags = {
            "postboot.stalwart.cluster_services": ",".join(cluster_services),
            "postboot.stalwart.node_id": node_id,
            "postboot.stalwart.node_roles": ",".join(node_roles),
        }

        instance_tags = self.tags
        instance_tags.update({"Name": name})
        instance_tags.update(postboot_tags)

        # User data includes a base64-encoded zip file. We must first produce that zip file.
        __archive_files = [
            "bootstrap.py",
            "templates/stalwart.toml.j2",
            "templates/thundermail.service.j2",
            "requirements.txt",
        ]
        with ZipFile(user_data_archive, "w") as archive:
            for file in __archive_files:
                archive.write(file)

        # Now read that file back in and base64-encode it
        with open(user_data_archive, "rb") as archive_fh:
            archive_data = archive_fh.read()

        encoded_archive = base64.encodebytes(archive_data)

        with open(user_data_template, "r") as fh:
            user_data_jinja = fh.read()
            user_data_values = {"bootstrap_zip_base64": encoded_archive}
            template = Template(user_data_jinja)
            user_data = template.render(user_data_values)

        # pulumi.info(f'USER DATA: {user_data}')

        # Sometimes we want to not apply changes to the AMI or user data, which would cause downtime. These features are
        # exposed through the component resource so users can more carefully control deployments.
        instance_ignores = []
        if ignore_ami_changes:
            instance_ignores.append("ami")
        if ignore_user_data_changes:
            instance_ignores.append("user_data")

        instance = aws.ec2.Instance(
            f"{name}-instance",
            ami=project.get_latest_amazon_linux_ami(),
            associate_public_ip_address=True,
            disable_api_stop=disable_api_stop,
            disable_api_termination=disable_api_termination,
            instance_type=instance_type,
            root_block_device={
                "delete_on_termination": False,  # TODO: What get stored here? Any reason to keep these?
                # "device_name": "/dev/xvda",
                "encrypted": True,
                "tags": self.tags,
                "volume_size": storage_capacity,
                "volume_type": "gp2",
            },
            subnet_id=subnet.id,
            tags=instance_tags,
            user_data=user_data,
            vpc_security_group_ids=[sg.resources["sg"].id],
            opts=pulumi.ResourceOptions(parent=self, ignore_changes=instance_ignores),
            **kwargs,
        )

        self.finish(resources={"sg": sg, "instance": instance})
