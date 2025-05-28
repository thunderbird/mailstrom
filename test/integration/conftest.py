import pytest
import time

from common.IMAP import IMAP
from common.SMTP import SMTP

from common.logger import log

from common.const import (
    MAILBOX_PREFIX,
    TEST_MSG_BODY_PREFIX,
    TEST_MSG_ATTACHMENT,
    TEST_MSG_SUBJECT_PREFIX,
    TEST_MSG_DEL_SUBJECT_PREFIX,
    TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX,
)

from const import (
    TEST_SERVER_HOST,
    SMTP_PORT,
    IMAP_PORT,
    CONNECT_TIMEOUT,
    TEST_ACCT_1_EMAIL,
    TEST_ACCT_2_EMAIL,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
    TEST_ACCT_2_USERNAME,
    TEST_ACCT_2_PASSWORD,
    IMAP_MSG_TESTS_EMAIL_COUNT,
    IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT,
    IMAP_MSG_TESTS_DEL_EMAIL_COUNT,
    IMAP_MSG_TESTS_EMAIL_WITH_ATTACHMENT_COUNT,
)


@pytest.fixture(scope='session')
def imap():
    """
    This fixture runs only once per entire test session, when included in any test definition.
    Before the tests start login to the IMAP server and provide the imap connection instance.
    Only login once per test session; the same login will be used by all of the tests in the session).
    """
    imap = IMAP(TEST_SERVER_HOST, IMAP_PORT, CONNECT_TIMEOUT)
    success = imap.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
    assert success, 'expected auth to be successful'
    yield imap

    # this runs after all of the tests in the class are finished; log out of the IMAP server
    if success:
        imap.close_mailbox()  # close any open mailbox
        signed_out = imap.logout()
        assert signed_out, 'expected logout to be successful'


@pytest.fixture(scope='session')
def smtp():
    """
    This fixture runs only once per entire test session, when included in any test definition.
    Before the tests start login to the SMTP server and provide the SMTP connection instance.
    Only login once per test session; the same login will be used by all of the tests in the session).
    """
    smtp = SMTP(TEST_SERVER_HOST, SMTP_PORT, CONNECT_TIMEOUT)
    success = smtp.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
    assert success, 'expected smtp auth to be successful'
    yield smtp

    # this runs after all of the tests in the class are finished; log out of the SMTP server
    if success:
        signed_out = smtp.logout()
        assert signed_out, 'expected smtp logout to be successful'


@pytest.fixture(scope='session', autouse=True)
def setup_env():
    """
    This fixture automatically runs only once per entire test session. If there is any setup that needs
    to be done before all of the tests start, do it here. For example if there are any Thundermail
    options that we wish to set. Here we are cleaning up previous mailboxes that were created by these
    tests. We do it here at the start so that we can always go in and look at the email account mailboxes
    if we want to check the state after the tests ran (but before running them again).
    """
    imap = IMAP(TEST_SERVER_HOST, IMAP_PORT, CONNECT_TIMEOUT)
    success = imap.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
    assert success, 'expected imap auth to be successful'

    log.debug('cleaning up test mailboxes')
    imap.cleanup_test_mailboxes(MAILBOX_PREFIX)

    log.debug('cleaning up test emails')
    imap.cleanup_test_messages(
        [TEST_MSG_SUBJECT_PREFIX, TEST_MSG_DEL_SUBJECT_PREFIX, TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX]
    )

    log.debug('cleaning up draft test emails')
    imap.cleanup_draft_test_messages()

    # done with imap
    signed_out = imap.logout()
    assert signed_out, 'expected imap logout to be successful'
    log.debug('finished cleaning up mailboxes')


@pytest.fixture(scope='class')
def populate_inbox():
    """
    This fixture runs once automatically at the start of a test suite when pulled into the test class.
    Used to populate the test_acct_1 inbox with email messages that are requried to exist for the imap
    messaging tests; by sending email to test_acct_1 from test_acct_2.

    We can only send 10 messages per connection then have to disconnect and reconnect or else send will
    fail with Maximum number of messages per session exceeded error.

    Also we pause 1 second after sending each email to avoid rate limiting; although we are also rate
    limited if we send more than 25 emails per (hour?).
    """
    log.debug('populating test_acct_1 for imap messaging tests')

    # first check how many messags exist in the test_acct_1 inbox
    imap = IMAP(TEST_SERVER_HOST, IMAP_PORT, CONNECT_TIMEOUT)
    success = imap.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
    assert success, 'expected imap auth to be successful'

    before_count = imap.select_mailbox()  # inbox by default
    log.debug(f'inbox message count: {before_count}')

    # now sign into SMTP and send our messages
    smtp = SMTP(TEST_SERVER_HOST, SMTP_PORT, CONNECT_TIMEOUT)
    success = smtp.login(TEST_ACCT_2_USERNAME, TEST_ACCT_2_PASSWORD)
    assert success, 'expected smtp auth to be successful'

    for x in range(IMAP_MSG_TESTS_EMAIL_COUNT):
        if x != 0 and x % 10 == 0:
            log.debug("disconnecting and reconnecting smtp so we won't exceed sent messages per session")
            signed_out = smtp.logout()
            assert signed_out, 'expected smtp logout to be successful'
            success = smtp.login(TEST_ACCT_2_USERNAME, TEST_ACCT_2_PASSWORD)
            assert success, 'expected smtp auth to be successful'

        # send the email
        success = smtp.send_test_email(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            subject=f'{TEST_MSG_SUBJECT_PREFIX} {x + 1}',
            body=TEST_MSG_BODY_PREFIX,
            attachment=None,
        )
        assert success, 'expected to be able to send email via smtp'
        time.sleep(1)

    # also we need to create some messages to be used for delete tests (special subject)
    for x in range(IMAP_MSG_TESTS_DEL_EMAIL_COUNT):
        if x != 0 and x % 10 == 0:
            log.debug("disconnecting and reconnecting smtp so we won't exceed sent messages per session")
            signed_out = smtp.logout()
            assert signed_out, 'expected smtp logout to be successful'
            success = smtp.login(TEST_ACCT_2_USERNAME, TEST_ACCT_2_PASSWORD)
            assert success, 'expected smtp auth to be successful'

        # send the email
        success = smtp.send_test_email(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            subject=f'{TEST_MSG_DEL_SUBJECT_PREFIX} {x + 1}',
            body=TEST_MSG_BODY_PREFIX,
            attachment=None,
        )
        assert success, 'expected to be able to send email via smtp'
        time.sleep(1)

    # also we need to create some messages with attachments (special subject too)
    for x in range(IMAP_MSG_TESTS_EMAIL_WITH_ATTACHMENT_COUNT):
        if x != 0 and x % 10 == 0:
            log.debug("disconnecting and reconnecting smtp so we won't exceed sent messages per session")
            signed_out = smtp.logout()
            assert signed_out, 'expected smtp logout to be successful'
            success = smtp.login(TEST_ACCT_2_USERNAME, TEST_ACCT_2_PASSWORD)
            assert success, 'expected smtp auth to be successful'

        # send the email
        success = smtp.send_test_email(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            subject=f'{TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX} {x + 1}',
            body=TEST_MSG_BODY_PREFIX,
            attachment=TEST_MSG_ATTACHMENT,
        )
        assert success, 'expected to be able to send email with attachment via smtp'
        time.sleep(1)

    # now create our draft test messages
    for x in range(IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT):
        success = imap.create_draft_email(
            from_address=TEST_ACCT_1_EMAIL,
            to_address=TEST_ACCT_2_EMAIL,
            subject=f'{TEST_MSG_SUBJECT_PREFIX} Draft {x + 1}',
        )
        assert success, 'expected to be able to create draft email via imap'
        time.sleep(1)

    draft_count = imap.select_mailbox('Drafts')
    assert draft_count >= IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT, (
        f'expected {IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT} draft messages to exist'
    )

    # done with smtp
    signed_out = smtp.logout()
    assert signed_out, 'expected smtp logout to be successful'

    # wait for all test messages to have been received by test_acct_1 before continuing
    max_checks = 6
    wait_seconds = 5
    all_arrived = False
    _exp_msg_count = (
        before_count
        + IMAP_MSG_TESTS_EMAIL_COUNT
        + IMAP_MSG_TESTS_DEL_EMAIL_COUNT
        + IMAP_MSG_TESTS_EMAIL_WITH_ATTACHMENT_COUNT
    )

    for checks in range(1, max_checks + 1):
        log.debug(
            f'waiting {wait_seconds} seconds for messages to arrive in test_acct_1 inbox '
            f'(check {checks} of {max_checks})'
        )
        time.sleep(wait_seconds)
        after_count = imap.select_mailbox()  # inbox by default
        log.debug(f'inbox message count is now: {after_count}')
        if after_count >= (before_count + IMAP_MSG_TESTS_EMAIL_COUNT + IMAP_MSG_TESTS_DEL_EMAIL_COUNT):
            all_arrived = True
            break

    assert all_arrived, 'failed populating inbox: expected all sent messages to have been received'

    # done with imap
    signed_out = imap.logout()
    assert signed_out, 'expected imap logout to be successful'

    log.debug('finished populating test_acct_1')
