# const specific to the load tests

import os
from dotenv import find_dotenv, load_dotenv

# Load our env
load_dotenv(find_dotenv('.env.test'), override=False)

# host, ports, and test account credentials
TEST_SERVER_HOST = str(os.getenv('TEST_SERVER_HOST')).strip()
SMTP_PORT = int(os.getenv('TEST_SMTP_PORT'))
IMAP_PORT = int(os.getenv('TEST_IMAP_PORT'))
TEST_CALDAV_URL = f'https://{TEST_SERVER_HOST}/dav/cal'
TEST_CARDDAV_URL = f'https://{TEST_SERVER_HOST}/dav/card'

CONNECT_TIMEOUT = 10  # seconds
LOAD_TEST_USERS_CSV = './test_files/.load_test_users.csv'

# test email and associated credentials where the load test emails will be sent to (same server)
LOAD_TEST_TO_EMAIL = str(os.getenv('LOAD_TEST_TO_EMAIL')).strip()
LOAD_TEST_TO_EMAIL_ACCT_USERNAME = str(os.getenv('LOAD_TEST_TO_EMAIL_ACCT_USERNAME')).strip()
LOAD_TEST_TO_EMAIL_ACCT_PASSWORD = str(os.getenv('LOAD_TEST_TO_EMAIL_ACCT_PASSWORD')).strip()

# load test data
LOAD_TEST_EMAIL_SUBJECT_PREFIX = 'Mailstrom Load Test'
LOAD_TEST_EMAIL_BODY_PREFIX = 'Sent by the mailstrom load tests.'
LOAD_TEST_FOLDER_NAME_PREFIX = 'Mailstrom Folder Load Test'
LOAD_TEST_EMAIL_HTML_BODY_PREFIX = '<html><body><h1>Sent by the mailstrom load tests (HTML).</h1></body></html>'
LOAD_TEST_CALENDAR_NAME_PREFIX = 'Mailstrom Load Test Calendar'
LOAD_TEST_EVENT_NAME_PREFIX = 'Mailstrom Load Test Event'
LOAD_TEST_ADDRESS_BOOK_NAME_PREFIX = 'Mailstrom Load Test Address Book'
LOAD_TEST_CONTACT_NAME_PREFIX = 'Mailstrom Load Test Contact'

# logging level
LOG_LEVEL = str(os.getenv('LOG_LEVEL', 'INFO')).strip()
