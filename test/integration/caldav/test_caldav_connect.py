from common.CalDAV import CalDAV
from urllib.parse import quote

from const import (
    TEST_CALDAV_URL,
    CONNECT_TIMEOUT,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


class TestCaldavConnect:
    def test_caldav_connect(self):
        caldav = CalDAV(TEST_CALDAV_URL, CONNECT_TIMEOUT)
        login_success = caldav.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert login_success, 'expected to be able to connect to caldav server'

        # verify calendar is supported
        support_list = caldav.client.check_dav_support()
        assert 'calendar' in support_list, 'expected calendar to be supported'

        # check principal
        assert quote(TEST_ACCT_1_USERNAME) in str(caldav.principal.url), 'expected caldav principal url to be correct'

        caldav.logout()
