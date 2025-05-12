# Mailstrom Load Tests


## Installation

The [main README](../../README.md) has instructions on working in a virtual environment for local development. Follow
those instructions to activate one and install dependencies for tests.


## Environment Setup

The load tests need a stage mailstrom test account (and associated credentials) that already exist on the stage host server, as well as the port info.
The test account must have a mailstrom email address set up with it already.

**Note:**
The tests will leave behind lots of data (i.e. mailboxes/folders/emails) so it is highly recommended you use mailstrom test accounts and not your own personal account.

Provide your mailstrom test account info in a local .env.test file as follows:

```bash
cd test/load
cp .env.test.example .env.test 
```

The `.env.test` file is in the gitignore as to prevent checking it into github by mistake! Open the `.env.test` file and
add the following values:

```
TEST_SERVER_HOST = "<server.name.here>"
TEST_SMTP_PORT = 465
LOAD_TEST_ACCT_USERNAME = "<username>"
LOAD_TEST_ACCT_PASSWORD = "<password>"
LOAD_TEST_ACCT_EMAIL = "<email address assocated with test_acct creds>" # msgs will be sent from here
LOAD_TEST_TO_EMAIL = "<email address to receive test messages>" # msgs will be sent to here
```


## Specify Load Test Config

Edit the `test/load/locust.conf` and set the parameters for the load test.

## Run the Load Tests

### Using the locust command line

```bash
cd test/load
locust -f <load-test-name.py>
```

### Enable debug logging

```bash
locust -f <load-test-name.py> --loglevel=DEBUG
```

### View the locust results

After running the tests locust writes an HTML results report which includes performance numbers and charts.
The report will be found at `/mailstrom/test/load/locust-output/locust-report.html`.

### Using the locust dashboard

Locust provides a front-end dashboard for running the tests and viewing results real-time. To run the tests using the locust dashboard modify the `test/load/locust.conf` file and comment out the `headless` option; then run the tests as normal:

```bash
locust -f <load-test-name.py>
```

When prompted, in the terminal press <ENTER> and the locust dashboard will open in your browser.
k