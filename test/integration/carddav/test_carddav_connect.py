from common.CardDAV import CardDAV
from urllib.parse import quote

from const import (
    TEST_CARDDAV_URL,
    CONNECT_TIMEOUT,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


class TestCaldavConnect:
    def test_carddav_connect(self):
        carddav = CardDAV(TEST_CARDDAV_URL, CONNECT_TIMEOUT)
        login_success = carddav.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert login_success, 'expected to be able to connect to carddav server'

        # verify address book is supported
        support_list = carddav.client.check_dav_support()
        assert 'addressbook' in support_list, 'expected address book to be supported'

        # check principal
        assert quote(TEST_ACCT_1_USERNAME) in str(carddav.principal.url), 'expected carddav principal url to be correct'
        carddav.logout()
