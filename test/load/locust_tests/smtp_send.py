import datetime
import sys
from locust import constant, task

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.SMTP import SMTP
from common.logger import log

from MailstromUser import MailstromUser

from const import (
    TEST_SERVER_HOST,
    SMTP_PORT,
    CONNECT_TIMEOUT,
    LOAD_TEST_TO_EMAIL,
    LOAD_TEST_EMAIL_SUBJECT_PREFIX,
    LOAD_TEST_EMAIL_HTML_BODY_PREFIX,
)


class MailstromSMTPUser(MailstromUser):
    # each task is repeated over and over by each test user; wait N seconds after each task is run
    wait_time = constant(2)
    email_count = 0
    connection = None
    test_user = None

    def on_start(self):
        # runs one time for each user (when the user is spun-up)
        self.email_count = 0

        # each user instance grabs one unique test account/credentials
        self.test_user = self.get_next_user()

        log.debug(f'user instance {id(self)}: signing in to smtp with username: {self.test_user["username"][:3]}***')
        self.connection = SMTP(TEST_SERVER_HOST, SMTP_PORT, CONNECT_TIMEOUT, locust=True)

        success = self.connection.login(self.test_user['username'], self.test_user['password'])
        if not success:
            # exit this user instance but locust test will continue with other users
            raise Exception(f'user instance {id(self)} smtp sign-in failed!')

    @task
    # this task will be repeated over and over by each user (until the test run-time is met)
    def smtp_send_email(self):
        # send email via smtp from our load test account
        self.email_count += 1

        # smtp rate limited to sending 10 emails per session, must reconnect to avoid
        if self.email_count % 10 == 0:
            log.debug(
                f'user instance {id(self)} {self.test_user["username"][:3]}***: disconnecting and '
                + 'reconnecting smtp to avoid session rate limiting'
            )
            signed_out = self.connection.logout()
            assert signed_out, 'expected smtp logout to be successful'
            success = self.connection.login(self.test_user['username'], self.test_user['password'])
            assert success, 'expected smtp login to be successful'

        log.debug(
            f'user instance {id(self)} {self.test_user["username"][:3]}***: sending email message '
            + f'{self.email_count} via smtp'
        )
        subject = (
            f'{LOAD_TEST_EMAIL_SUBJECT_PREFIX} (user instance {id(self)} '
            + f'msg {self.email_count}) {datetime.datetime.now()}'
        )
        self.connection.send_test_email_multipart(
            to_email=LOAD_TEST_TO_EMAIL,
            from_email=self.test_user['email'],
            cc_email=None,
            bcc_email=None,
            subject=subject,
            plain_body=None,
            html_body=LOAD_TEST_EMAIL_HTML_BODY_PREFIX,
            attachment=None,
        )

    def on_stop(self):
        # runs one time for each user (when the tests are finished )
        log.debug(f'user instance {id(self)}: signing out of smtp')
        self.connection.logout()
