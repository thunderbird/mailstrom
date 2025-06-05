# Mailstrom Load Tests


## Installation

The [main README](../../README.md) has instructions on working in a virtual environment for local development. Follow
those instructions to activate one and install dependencies for tests.


## Environment Setup

Before running the tests you must provide the following load test information.

### Server Host and Ports

Provide your mailstrom stage server and port info in a local `.env.test` file as follows:

```bash
cd test/load
cp .env.test.example .env.test 
```

The `.env.test` file is in the gitignore as to prevent checking it into github by mistake! Open the `.env.test` file and
add the following values:

```dotenv
TEST_SERVER_HOST = "<server.name.here>"
TEST_SMTP_PORT = 465
TEST_IMAP_PORT = 993
```

### Stage Test Account to Receive Emails

The load tests send emails to a specified email address; you must provide the stage account credentials and associated email address where the load tests will send test emails to.

**Note:**
The tests will leave behind lots of data (i.e. mailboxes/folders/emails) so it is highly recommended you use mailstrom test accounts and not your own personal accounts!

To specify where the load tests will send test emails, open the same `.env.test` file and add the following info:

```dotenv
LOAD_TEST_TO_EMAIL = "<email address to receive test messages>" # msgs will be sent to here
LOAD_TEST_TO_EMAIL_ACCT_USERNAME = "<username>"
LOAD_TEST_TO_EMAIL_ACCT_PASSWORD = "<password>"
```

### User Test Account Credentials & Email Addresses

The load tests sign in to mailstrom with multiple users and perform load test tasks for each user (in parallel). Stage server test accounts must already exist to be used with the load tests. You provide the credentials for these test accounts in a local `.load_test_users.csv` file. This file is in the .gitignore; be sure to NEVER check this file into the repo!

**Note:**
The tests will leave behind lots of data (i.e. mailboxes/folders/emails) so it is highly recommended you use mailstrom test accounts and not your own personal accounts!

The following information is required for each mailstrom load test account:

stage-server-username: The mailstrom stage test account username<br>
user-password: The mailstrom stage test account user password<br>
user-email-address: The mailstrom email address that is already configured and exists for the given mailstrom user

To provide the test account user information for the load test, create a local `test/load/.load_test_users.csv` CSV file.<br>
Add a line in the CSV file for each stage load test account, using the following format for each line/user:

`stage-server-username,user-password,user-email-address`

## Specify Load Test Config

Edit the `test/load/locust.conf` and set the parameters for the load test. Important: You must have existing test account credentials for the number of users that you specify in the `locust.conf` file `users` option. For example, if you specify in the `locust.conf` that you want to run the load test with `users 10`, then you need to have the credentials and email addresses for `10 existing stage test accounts` provided in your `.load_test_users.csv` file, as noted above.


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
