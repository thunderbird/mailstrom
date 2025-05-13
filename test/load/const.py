import os
from dotenv import find_dotenv, load_dotenv

# Load our env
load_dotenv(find_dotenv('.env.test'), override=True)

TEST_SERVER_HOST = str(os.getenv('TEST_SERVER_HOST')).strip()
SMTP_PORT = int(os.getenv('TEST_SMTP_PORT'))
CONNECT_TIMEOUT = 10 # seconds
LOAD_TEST_ACCT_USERNAME = str(os.getenv('LOAD_TEST_ACCT_USERNAME')).strip()
LOAD_TEST_ACCT_PASSWORD = str(os.getenv('LOAD_TEST_ACCT_PASSWORD')).strip()
LOAD_TEST_ACCT_EMAIL = str(os.getenv('LOAD_TEST_ACCT_EMAIL')).strip()
LOAD_TEST_TO_EMAIL = str(os.getenv('LOAD_TEST_TO_EMAIL')).strip()
LOAD_TEST_EMAIL_SUBJECT_PREFIX = 'Mailstrom Load Test'
LOAD_TEST_EMAIL_BODY_PREFIX = 'Sent by the mailstrom load tests.'
