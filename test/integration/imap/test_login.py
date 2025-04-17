
from const import TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD
from IMAP import IMAP


class TestIMAPAuth:
    def test_login_logout(self):
        imap = IMAP()
        success = imap.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert success, 'expected auth to be successful'

        # retrieve imap server capabilities
        status, capabilities = imap.get_capabilities()
        assert status == 'OK', 'expected to be able to retrieve server capabilities'
        assert capabilities, 'expected capabilities to be returned'

        # log out server
        success = imap.logout()
        assert success, 'expected logout to be successful'
