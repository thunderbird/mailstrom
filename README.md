# Thunderbird Pro Mail Service Prototype

## How Stalwart Node Bootstrapping Works

In the broadest strokes:

- The `bootstrap` directory contains a script and related files that will eventually run on a Stalwart node at launch
  time.
- The `stalwart.StalwartClusterNode` class zips up these bootstrapping files, base64-encodes the zip, and injects that
  string into a script (stalwart_instance_user_data.sh.j2).
- That script gets set as the instance's user data script, such that when the instance is first launched, the script
  runs.
- This first stage script unpacks the zip file and runs the second stage Python script contained therein.
- The second stage script templates a config file for Stalwart and a systemd service file that runs it as a docker
  container when the instance comes online.

In this way, a `pulumi up` with a proper node configuration can bootstrap a functioning Stalwart node in a minute or so.