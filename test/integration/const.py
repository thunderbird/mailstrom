import os
from dotenv import find_dotenv, load_dotenv

# Load our env
load_dotenv(find_dotenv('.env.test'), override=True)

# IMAP host to connect to
IMAP_HOST = str(os.getenv('TEST_IMAP_HOST')).strip()
IMAP_PORT = int(os.getenv('TEST_IMAP_PORT'))

# Test accounts that exist on the IMAP host
TEST_ACCT_1_USERNAME = str(os.getenv('TEST_ACCT_1_USERNAME')).strip()
TEST_ACCT_1_PASSWORD = str(os.getenv('TEST_ACCT_1_PASSWORD')).strip()

# Default mailboxes expected to exist
DEFAULT_MAILBOX_LIST = [
    {'flags': '()', 'separator': '"/"', 'name': 'Deleted Items'},
    {'flags': '()', 'separator': '"/"', 'name': 'Drafts'},
    {'flags': '()', 'separator': '"/"', 'name': 'INBOX'},
    {'flags': '()', 'separator': '"/"', 'name': 'Junk Mail'},
    {'flags': '()', 'separator': '"/"', 'name': 'Sent Items'},
]

# Prefix used when creating mailboxes/folders
MAILBOX_PREFIX = 'AutoTest'

# Connection states
STATE_NONAUTH = 'NONAUTH'
STATE_AUTH = 'AUTH'
STATE_LOGOUT = 'LOGOUT'
STATE_SELECTED = 'SELECTED'

# Return values from IMAP commands
LOGOUT_BYE = 'BYE'
RESULT_OK = 'OK'
RESULT_NO = 'NO'
ALREADY_EXISTS = b'already exists'
NOT_FOUND = b'not found'
MISSING_ARGS = b'Missing arguments'
MAILBOX_CREATED = b'Mailbox created'
MAILBOX_SUBSCRIBED = b'Mailbox subscribed'
MAILBOX_ALREADY_SUBSCRIBED = b'Mailbox is already subscribed'
MAILBOX_ALREADY_UNSUBSCRIBED = b'Mailbox is already unsubscribed'
MAILBOX_DELETED = b'Mailbox deleted'
MAILBOX_UNSUBSCRIBED = b'Mailbox unsubscribed'
MAILBOX_NAME_MISSING = b'Missing mailbox name'
MAILBOX_NOT_EXIST = b'Mailbox does not exist'
MAILBOX_RENAMED = b'RENAME completed'
INVALID_FOLDER_NAME = b'Invalid folder name'
MAILBOX_HAS_CHILD = b'Mailbox has at least one children'
MAILBOX_CLOSE_COMPLETED = b'CLOSE completed'
MAILBOX_CLOSE_ILLEGAL_STATE = 'command CLOSE illegal in state AUTH, only allowed in states SELECTED'
