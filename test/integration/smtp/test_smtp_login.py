import time

from const import (
    TEST_SERVER_HOST,
    SMTP_PORT,
    CONNECT_TIMEOUT,
    TEST_ACCT_2_USERNAME,
    TEST_ACCT_2_PASSWORD,
    TEST_ACCT_2_EMAIL,
)

from common.SMTP import SMTP
from common.logger import log


class TestSMTPAuth:
    def test_login_logout(self):
        smtp = SMTP(TEST_SERVER_HOST, SMTP_PORT, CONNECT_TIMEOUT)
        success = smtp.login(TEST_ACCT_2_USERNAME, TEST_ACCT_2_PASSWORD)
        assert success, 'expected smtp auth to be successful'
        time.sleep(3)

        log.debug(f'verifying user {TEST_ACCT_2_EMAIL[:3]}*** with SMTP server')
        result, data = smtp.connection.verify(TEST_ACCT_2_EMAIL)
        log.debug(f'{result}, {data[:3]}***')
        assert result == 250, 'expected smtp verify to return 250'
        assert TEST_ACCT_2_EMAIL in data.decode(), 'expected test acct email address to be returned by smtp verify'

        success = smtp.logout()
        assert success, 'expected smtp logout to be successful'
