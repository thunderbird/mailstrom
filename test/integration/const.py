# Const specific to the integration tests

import os
from dotenv import find_dotenv, load_dotenv

# Load our env
load_dotenv(find_dotenv('.env.test'), override=True)

# Mailstrom test server connection info
TEST_SERVER_HOST = str(os.getenv('TEST_SERVER_HOST')).strip()
IMAP_PORT = int(os.getenv('TEST_IMAP_PORT'))
SMTP_HOST = str(os.getenv('TEST_SMTP_HOST')).strip()
SMTP_PORT = int(os.getenv('TEST_SMTP_PORT'))
CONNECT_TIMEOUT = 10  # seconds

# Test accounts that already exist
TEST_ACCT_1_USERNAME = str(os.getenv('TEST_ACCT_1_USERNAME')).strip()
TEST_ACCT_1_PASSWORD = str(os.getenv('TEST_ACCT_1_PASSWORD')).strip()
TEST_ACCT_1_EMAIL = str(os.getenv('TEST_ACCT_1_EMAIL')).strip()

TEST_ACCT_2_USERNAME = str(os.getenv('TEST_ACCT_2_USERNAME')).strip()
TEST_ACCT_2_PASSWORD = str(os.getenv('TEST_ACCT_2_PASSWORD')).strip()
TEST_ACCT_2_EMAIL = str(os.getenv('TEST_ACCT_2_EMAIL')).strip()

# Default mailboxes expected to exist
DEFAULT_MAILBOX_LIST = [
    {'flags': '()', 'separator': '"/"', 'name': 'Deleted Items'},
    {'flags': '()', 'separator': '"/"', 'name': 'Drafts'},
    {'flags': '()', 'separator': '"/"', 'name': 'INBOX'},
    {'flags': '()', 'separator': '"/"', 'name': 'Junk Mail'},
    {'flags': '()', 'separator': '"/"', 'name': 'Sent Items'},
]

# Number of emails required in the inbox for the IMAP messaging tests, and their details
IMAP_MSG_TESTS_EMAIL_COUNT = 5
IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT = 1
IMAP_MSG_TESTS_DEL_EMAIL_COUNT = 3
IMAP_MSG_TESTS_EMAIL_WITH_ATTACHMENT_COUNT = 1
