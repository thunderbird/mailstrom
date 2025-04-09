# Mail Service Prototype Deployment Code

This is the code for the mailstrom project in Pulumi, it currently only has one stack: dev.

All resources are managed by Pulumi except for the Neon database connection and the Elastic IP used as the main outgoing address, because we will likely want to reuse that in the production setup for IP reputation reasons.

All user data is in Neon and in the S3 bucket, so only those need to be preserved when modifying this stack.
