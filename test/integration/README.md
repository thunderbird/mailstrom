# Mailstrom Integration Tests

The purpose of the integration tests is to verify basic IMAP/SMTP/JMAP support on a running mailstrom instance.


## Installation

The [main README](../../README.md) has instructions on working in a virtual environment for local development. Follow
those instructions to activate one and install dependencies for tests.


## Environment Setup

The integration tests need two mailstrom test accounts (and associated credentials) that already exist on the host server, as well as the port info.
Each test account must have a mailstrom (Thundermail) email address set up with it already, and an associated app password (ie. setup in TB Accounts).

**Note:**
The tests will leave behind data (i.e. mailboxes/folders/emails) so it is highly recommended you use mailstrom test accounts and not your own personal account. For the account password you use the app password that you created in TB Accounts, NOT the password you used to sign into TB Accounts itself.

Provide your mailstrom test accounts info in a local .env.test file as follows:

```bash
cd test/integration
cp .env.test.example .env.test 
```

The `.env.test` file is in the gitignore as to prevent checking it into github by mistake! Open the `.env.test` file and
add the following values:

```
TEST_SERVER_HOST = "<your mailstrom server host name>"
TEST_IMAP_PORT = <your mailstrom IMAP server port>
TEST_SMTP_PORT = <your mailstrom SMTP server port>
TEST_JMAP_PORT = <your mailstrom JMAP server port>

TEST_ACCT_1_USERNAME = "<email address / username that exists on the host>"
TEST_ACCT_1_PASSWORD = "<associated app password>"
TEST_ACCT_1_EMAIL = "email address assocated with test_acct_1 creds"

TEST_ACCT_2_USERNAME = "<email address / username that exists on the host>"
TEST_ACCT_2_PASSWORD = "<associated app password>"
TEST_ACCT_2_EMAIL = "email address assocated with test_acct_2 creds"
```


## Test Data

The integration tests automatically create the test data they need. For example, the IMAP messaging tests require a certain number of email messages to exist in the test_acct_1 inbox; before the messaging tests start the test_acct_1 inbox is automatically populated by the required test emails via a python test fixture that uses SMTP.

When the integration tests start they will clean up any mailboxes/folders and emails that were created in the past by prevous integration test runs. All mailboxes/folders and emails used by the integration tests use spcific labels that are easy to find and clean up. The integration tests follow this flow when they run:

- Cleans up mailboxes/folders and emails created by previous test runs
- Creates new test data (emails etc.) that the tests require
- Runs the integration tests and uses the test data that was created
- After the tests are finished, if you need to debug failures, the test environment still remains. The mailboxes/folders and test emails that were created still remain on the server, so you can debug by looking at the state via Thunderbird etc. The test data will remain intact until you run integration test suite again.


## Run the Tests

Run the integration tests via pytest:

```bash
cd test/integration
python -m pytest -vs
```

### Enable debug logging

To enable debug logging for the integration tests, edit the `.env.test` file and set:

```dotenv
LOG_LEVEL = 'DEBUG'
```
