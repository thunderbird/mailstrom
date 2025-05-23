# Mailstrom Load Tests


## Installation

The [main README](../../README.md) has instructions on working in a virtual environment for local development. Follow
those instructions to activate one and install dependencies for tests.


## Environment Setup

The load tests need two stage mailstrom test accounts (and associated credentials) that already exist on the stage host server, as well as the port info.
The test accounts must have a mailstrom email address set up with it already. One test account is used to send the email messages and the other is where the emails will be received.

**Note:**
The tests will leave behind lots of data (i.e. mailboxes/folders/emails) so it is highly recommended you use mailstrom test accounts and not your own personal accounts.

Provide your mailstrom test accounts info in a local .env.test file as follows:

```bash
cd test/load
cp .env.test.example .env.test 
```

The `.env.test` file is in the gitignore as to prevent checking it into github by mistake! Open the `.env.test` file and
add the following values:

```dotenv
TEST_SERVER_HOST = "<server.name.here>"
TEST_SMTP_PORT = 465

LOAD_TEST_ACCT_USERNAME = "<username>"
LOAD_TEST_ACCT_PASSWORD = "<password>"
LOAD_TEST_ACCT_EMAIL = "<email address assocated with test_acct creds>" # msgs will be sent from here

LOAD_TEST_TO_EMAIL = "<email address to receive test messages>" # msgs will be sent to here
LOAD_TEST_TO_EMAIL_ACCT_USERNAME = "<username>" # creds to access the to email
LOAD_TEST_TO_EMAIL_ACCT_PASSWORD = "<password>"
```

## Specify Load Test Config

Edit the `test/load/locust.conf` and set the parameters for the load test.


## Run the Load Tests

### Using the locust command line

```bash
cd test/load
locust -f locust-tests/<load-test-name.py>
```

### Enable debug logging

To enable debug logging for the load tests, edit the `.env.test` file and set:

```dotenv
LOG_LEVEL = 'DEBUG'
```

### View the locust results

After running the tests locust writes an HTML results report which includes performance numbers and charts.
The report will be found at `/mailstrom/test/load/locust-output/locust-report.html`.

### Using the locust dashboard

Locust provides a front-end dashboard for running the tests and viewing results real-time. To run the tests using the locust dashboard modify the `test/load/locust.conf` file and comment out the `headless` option; then run the tests as normal:

```bash
locust -f locust-tests/<load-test-name.py>
```

When prompted, in the terminal press <ENTER> and the locust dashboard will open in your browser.

### Cleaning up load test data

A script is available to delete the emails and folders in the test account left behind by the load tests. The load tests create emails and folders/mailboxes using specific prefixes, the script searches for emails/folders with those prefixes and deletes them.

To run the load test clenaup script:

```bash
cd test/load
python cleanup.py
```
