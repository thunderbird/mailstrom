import pytest

from const import TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD
from IMAP import IMAP


@pytest.fixture(scope='session')
def imap():
    """
    This fixture runs only once per entire test session, when included in any test definition.
    Before the tests start login to the IMAP server and provide the imap connection instance.
    Only login once per test session; the same login will be used by all of the tests in the session).
    """
    imap = IMAP()
    success = imap.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
    assert success, 'expected auth to be successful'
    yield imap

    # this runs after all of the tests in the class are finished; log out of the IMAP server
    if success:
        imap.close_mailbox()  # close any open mailbox
        signed_out = imap.logout()
        assert signed_out, 'expected logout to be successful'


@pytest.fixture(scope='session', autouse=True)
def setup_env():
    """
    This fixture automatically runs only once per entire test session. If there is any setup that needs
    to be done before all of the tests start, do it here. For example if there are any Thundermail
    options that we wish to set. Here we are cleaning up previous mailboxes that were created by these
    tests. We do it here at the start so that we can always go in and look at the email account mailboxes
    if we want to check the state after the tests ran (but before running them again).
    """
    print('\ncleaning up test mailboxes')
    imap = IMAP()
    success = imap.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
    assert success, 'expected auth to be successful'

    imap.cleanup_test_mailboxes()
    signed_out = imap.logout()
    assert signed_out, 'expected logout to be successful'
