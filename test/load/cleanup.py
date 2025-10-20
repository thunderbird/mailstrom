import csv
import sys
import time

sys.path.append('../')
from common.IMAP import IMAP
from common.logger import log

from const import (
    TEST_SERVER_HOST,
    IMAP_PORT,
    CONNECT_TIMEOUT,
    LOAD_TEST_USERS_CSV,
    LOAD_TEST_FOLDER_NAME_PREFIX,
    LOAD_TEST_TO_EMAIL_ACCT_USERNAME,
    LOAD_TEST_TO_EMAIL_ACCT_PASSWORD,
    LOAD_TEST_EMAIL_SUBJECT_PREFIX,
)

imap = IMAP(TEST_SERVER_HOST, IMAP_PORT, CONNECT_TIMEOUT)

USER_CREDENTIALS = []


# warn that this will delete the load test data from previous load test runs
print(
    '\nWarning: This will delete all folders and emails left behind from any '
    'previous load test runs, for all load test accounts.'
)
confirm = input('Continue? (Y/N): ')
if confirm.strip().upper() != 'Y':
    exit(0)

log.info('cleaning up data left behind by load tests')
# grab our mailstrom load test users from our local user credentials file
try:
    with open(LOAD_TEST_USERS_CSV, newline='') as creds_csv:
        reader = csv.reader(creds_csv)
        for cred in reader:
            USER_CREDENTIALS.append({'username': cred[0], 'password': cred[1]})

except FileNotFoundError:
    raise Exception('local credentials file not found!')

# for each of our mailstrom test user accounts, sign in and delete any folders that were left
# eft behind by previous runs of the mailbox load tests
for test_account in USER_CREDENTIALS:
    log.debug(f'cleaning up previous load test data for test user {test_account["username"].split("@")[0]}')
    success = imap.login(test_account['username'], test_account['password'])

    if success:
        # first cleanup the folders, they were created in each load test account
        imap.cleanup_test_mailboxes(LOAD_TEST_FOLDER_NAME_PREFIX)
        imap.logout()

        time.sleep(3)
    else:
        # we aren't going to error out as we're just cleaning up old data
        log.debug(f'failed to sign into test account {test_account["username"].split("@")[0]}')

# now cleanup any emails that were left behind by previous runs of the send mail load test
# (the test sent emails to LOAD_TEST_TO_EMAIL in the LOAD_TEST_TO_EMAIL_ACCT)
log.info(f'now cleaning up emails that were received by {LOAD_TEST_TO_EMAIL_ACCT_USERNAME.split("@")[0]}')
success = imap.login(LOAD_TEST_TO_EMAIL_ACCT_USERNAME, LOAD_TEST_TO_EMAIL_ACCT_PASSWORD)
assert success, 'expected to be able to sign into imap'
imap.cleanup_test_messages([LOAD_TEST_EMAIL_SUBJECT_PREFIX])
imap.logout()

log.info('finished cleaning up load test data')
