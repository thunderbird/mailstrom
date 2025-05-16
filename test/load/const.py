# const specific to the load tests

import os
from dotenv import find_dotenv, load_dotenv

# Load our env
load_dotenv(find_dotenv('.env.test'), override=True)

# host, ports, and test account credentials
TEST_SERVER_HOST = str(os.getenv('TEST_SERVER_HOST')).strip()
SMTP_PORT = int(os.getenv('TEST_SMTP_PORT'))
IMAP_PORT = int(os.getenv('TEST_IMAP_PORT'))
CONNECT_TIMEOUT = 10  # seconds

LOAD_TEST_ACCT_USERNAME = str(os.getenv('LOAD_TEST_ACCT_USERNAME')).strip()
LOAD_TEST_ACCT_PASSWORD = str(os.getenv('LOAD_TEST_ACCT_PASSWORD')).strip()
LOAD_TEST_ACCT_EMAIL = str(os.getenv('LOAD_TEST_ACCT_EMAIL')).strip()

# test email and associated credentials where the load test emails will be sent to (same server)
LOAD_TEST_TO_EMAIL = str(os.getenv('LOAD_TEST_TO_EMAIL')).strip()
LOAD_TEST_TO_EMAIL_ACCT_USERNAME = str(os.getenv('LOAD_TEST_TO_EMAIL_ACCT_USERNAME')).strip()
LOAD_TEST_TO_EMAIL_ACCT_PASSWORD = str(os.getenv('LOAD_TEST_TO_EMAIL_ACCT_PASSWORD')).strip()

# load test data
LOAD_TEST_EMAIL_SUBJECT_PREFIX = 'Mailstrom Load Test'
LOAD_TEST_EMAIL_BODY_PREFIX = 'Sent by the mailstrom load tests.'
LOAD_TEST_FOLDER_NAME_PREFIX = 'Mailstrom Folder Load Test'
