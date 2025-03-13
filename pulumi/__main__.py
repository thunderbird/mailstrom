#!/bin/env python3

import tb_pulumi
import tb_pulumi.ec2
import tb_pulumi.network
import stalwart


# Create a project to aggregate resources. This will allow consistent tagging, resource protection,
# etc. The naming is derived from the currently selected Pulumi project/stack. A configuration file
# called `config.$stack.yaml` is loaded from the current directory. See config.stack.yaml.example.
project = tb_pulumi.ThunderbirdPulumiProject()

# Pull the "resources" config mapping
resources = project.config.get("resources")

# Let's say we want to build a VPC with some private IP space. We can do this with a `MultiCidrVpc`.
vpc_opts = resources["tb:network:MultiCidrVpc"]["vpc"]
vpc = tb_pulumi.network.MultiCidrVpc(
    # project.name_prefix combines the Pulumi project and stack name to create a unique prefix
    f"{project.name_prefix}-vpc",
    # Add this module's resources to the project
    project,
    # Map the rest of the config file directly into this function call, separating code from config
    **vpc_opts,
)

# Build a Stalwart cluster
stalwart_opts = resources["tb:mailstrom:StalwartCluster"]["thundermail"]
stalwart_cluster = stalwart.StalwartCluster(
    f"{project.name_prefix}-stalwart",
    project=project,
    subnets=vpc.resources["subnets"],
    **stalwart_opts,
)

jumphost_opts = resources["tb:ec2:SshableInstance"]["jumphost"]
jumphost = tb_pulumi.ec2.SshableInstance(
    f"{project.name_prefix}-jumphost",
    project=project,
    subnet_id=vpc.resources["subnets"][0].id,
    vpc_id=vpc.resources["vpc"].id,
    **jumphost_opts,
)
