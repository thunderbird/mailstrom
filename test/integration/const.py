# Const specific to the integration tests

import os
from dotenv import find_dotenv, load_dotenv

# Load our env
load_dotenv(find_dotenv('.env.test'), override=False)

# Mailstrom test server connection info
TEST_SERVER_HOST = str(os.getenv('TEST_SERVER_HOST')).strip()
IMAP_PORT = int(os.getenv('TEST_IMAP_PORT'))
SMTP_PORT = int(os.getenv('TEST_SMTP_PORT'))
JMAP_PORT = int(os.getenv('TEST_JMAP_PORT'))
CONNECT_TIMEOUT = 60  # (seconds) requests take longer in CI/GHA test env

# Expected JMAP capabilities
JMAP_CAPABILITY_CORE_MAX_SIZE_UPLOAD = 50000000
JMAP_CAPABILITY_CORE_MAX_CONCURRENT_UPLOAD = 4
JMAP_CAPABILITY_CORE_MAX_SIZE_REQUEST = 10000000
JMAP_CAPABILITY_CORE_MAX_CONCURRENT_REQUESTS = 4
JMAP_CAPABILITY_CORE_MAX_CALLS_IN_REQUEST = 16

# CalDAV
TEST_CALDAV_URL = f'https://{TEST_SERVER_HOST}/dav/cal'
CALDAV_EXP_DEFAULT_CALENDAR_NAME = 'Thundermail Calendar'

# CardDAV
TEST_CARDDAV_URL = f'https://{TEST_SERVER_HOST}/dav/card'
CARDDAV_EXP_DEFAULT_ADDRESS_BOOK_NAME = 'Thundermail Address Book'

# Test accounts that already exist
TEST_ACCT_1_USERNAME = str(os.getenv('TEST_ACCT_1_USERNAME')).strip()
TEST_ACCT_1_PASSWORD = str(os.getenv('TEST_ACCT_1_PASSWORD')).strip()
TEST_ACCT_1_EMAIL = str(os.getenv('TEST_ACCT_1_EMAIL')).strip()

TEST_ACCT_2_USERNAME = str(os.getenv('TEST_ACCT_2_USERNAME')).strip()
TEST_ACCT_2_PASSWORD = str(os.getenv('TEST_ACCT_2_PASSWORD')).strip()
TEST_ACCT_2_EMAIL = str(os.getenv('TEST_ACCT_2_EMAIL')).strip()

# Default mailboxes expected to exist (IMAP format)
DEFAULT_IMAP_MAILBOX_LIST = [
    {'flags': '()', 'separator': '"/"', 'name': 'Deleted Items'},
    {'flags': '()', 'separator': '"/"', 'name': 'Drafts'},
    {'flags': '()', 'separator': '"/"', 'name': 'INBOX'},
    {'flags': '()', 'separator': '"/"', 'name': 'Junk Mail'},
    {'flags': '()', 'separator': '"/"', 'name': 'Sent Items'},
]

# Number of test emails required for the IMAP/JMAP tests (our conftest.py 'populate_inbox' test fixture will
# create these emails when the IMAP messaging tests start and again when the JMAP messaging tests start)
MSG_TESTS_EMAIL_COUNT = 5
MSG_TESTS_DRAFT_EMAIL_COUNT = 1
MSG_TESTS_DEL_EMAIL_COUNT = 3
MSG_TESTS_EMAIL_WITH_ATTACHMENT_COUNT = 1

# logging level
LOG_LEVEL = str(os.getenv('LOG_LEVEL', 'INFO')).strip()

# Default mailboxes expected to exist (JMAP format)
DEFAULT_JMAP_MAILBOX_LIST = [
    {'id': 'a', 'name': 'Inbox', 'role': 'inbox'},
    {'id': 'b', 'name': 'Deleted Items', 'role': 'trash'},
    {'id': 'c', 'name': 'Junk Mail', 'role': 'junk'},
    {'id': 'd', 'name': 'Drafts', 'role': 'drafts'},
    {'id': 'e', 'name': 'Sent Items', 'role': 'sent'},
]

# JMAP mailbox with child deletion error
JMAP_DELETE_MAILBOX_WITH_CHILD_ERR = 'Mailbox has at least one children.'
