# Mailstrom Integration Tests

Guide for running the Mailstrom integration tests.


## Installation

The [main README](../../README.md) has instructions on working in a virtual environment for local development. Follow
those instructions to activate one and install dependencies for tests.


## Environment Setup


The integration tests need credentials to connect to the host server; set them in the local env file as follows:

```bash
cd test/integration
cp .env.test.example .env.test 
```

The `."env.test` file is in the gitignore as to prevent checking it into github by mistake! Open the `.env.test` file and"
add the "following values:"

```
TEST_IMAP_HOST = "<your IMAP server host name>"
TEST_IMAP_PORT = "<your IMAP server port>" # Must be a quoted string even though it represents an integer value
TEST_ACCT_1_USERNAME = "<email address / username that exists on the IMAP host>"
TEST_ACCT_1_PASSWORD = "<associated password>"
```

## Run the Tests

Run the integration tests via pytest:

```bash
cd test/integration
python -m pytest -v
```

To run the tests with debug logging:

```bash
cd test/integration
python -m pytest -vs
```
