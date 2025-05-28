import sys

sys.path.append('../')
from common.IMAP import IMAP
from common.logger import log

from const import (
    TEST_SERVER_HOST,
    IMAP_PORT,
    CONNECT_TIMEOUT,
    LOAD_TEST_ACCT_USERNAME,
    LOAD_TEST_ACCT_PASSWORD,
    LOAD_TEST_FOLDER_NAME_PREFIX,
    LOAD_TEST_TO_EMAIL_ACCT_USERNAME,
    LOAD_TEST_TO_EMAIL_ACCT_PASSWORD,
    LOAD_TEST_EMAIL_SUBJECT_PREFIX,
)

log.info('cleaning up data left behind by load tests')

imap = IMAP(TEST_SERVER_HOST, IMAP_PORT, CONNECT_TIMEOUT)
success = imap.login(LOAD_TEST_ACCT_USERNAME, LOAD_TEST_ACCT_PASSWORD)
assert success, 'expected to be able to sign into imap'

# first cleanup the folders, they were created in LOAD_TEST_ACCT
imap.cleanup_test_mailboxes(LOAD_TEST_FOLDER_NAME_PREFIX)
imap.logout()

# now cleanup the emails, the were sent to LOAD_TEST_TO_EMAIL in the LOAD_TEST_TO_EMAIL_ACCT
success = imap.login(LOAD_TEST_TO_EMAIL_ACCT_USERNAME, LOAD_TEST_TO_EMAIL_ACCT_PASSWORD)
assert success, 'expected to be able to sign into imap'

imap.cleanup_test_messages([LOAD_TEST_EMAIL_SUBJECT_PREFIX])
imap.logout()

log.info('finished cleaning up load test data')
