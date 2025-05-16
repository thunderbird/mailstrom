import datetime
import logging
import sys
from locust import User, constant, task

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.SMTP import SMTP

from const import (
    TEST_SERVER_HOST,
    SMTP_PORT,
    CONNECT_TIMEOUT,
    LOAD_TEST_ACCT_USERNAME,
    LOAD_TEST_ACCT_PASSWORD,
    LOAD_TEST_ACCT_EMAIL,
    LOAD_TEST_TO_EMAIL,
    LOAD_TEST_EMAIL_SUBJECT_PREFIX,
    LOAD_TEST_EMAIL_BODY_PREFIX,
)


class MailstromSMTPUser(User):
    # each task is repeated over and over by each test user; wait N seconds after each task is run
    # with 3 seconds wait, each user will send approximately 20 emails per minute when all spawned
    wait_time = constant(3)
    email_count = 0
    connection = None

    def on_start(self):
        # runs one time for each user (when the user is spun-up)
        self.email_count = 0
        logging.debug(f'user instance {id(self)}: signing in to smtp')
        self.connection = SMTP(TEST_SERVER_HOST, SMTP_PORT, CONNECT_TIMEOUT)
        success = self.connection.login(LOAD_TEST_ACCT_USERNAME, LOAD_TEST_ACCT_PASSWORD)
        assert success, 'expected smtp login to be successful'

    @task
    # this task will be repeated over and over by each user (until the test run-time is met)
    def smtp_send_email(self):
        # send email via smtp from our load test account
        self.email_count += 1

        # smtp rate limited to sending 10 emails per session, must reconnect to avoid
        if self.email_count % 10 == 0:
            logging.debug("disconnecting and reconnecting smtp so we won't exceed sent messages per session")
            signed_out = self.connection.logout()
            assert signed_out, 'expected smtp logout to be successful'
            success = self.connection.login(LOAD_TEST_ACCT_USERNAME, LOAD_TEST_ACCT_PASSWORD)
            assert success, 'expected smtp login to be successful'

        logging.debug(f'user instance {id(self)}: sending email message {self.email_count} via smtp')
        subject = f'{LOAD_TEST_EMAIL_SUBJECT_PREFIX} (user instance {id(self)} '
        f'msg {self.email_count}) {datetime.datetime.now()}'
        self.connection.send_test_email(
            LOAD_TEST_TO_EMAIL, LOAD_TEST_ACCT_EMAIL, subject, LOAD_TEST_EMAIL_BODY_PREFIX, attachment=None, locust=True
        )

    def on_stop(self):
        # runs one time for each user (when the tests are finished )
        logging.debug(f'user instance {id(self)}: signing out of smtp')
        self.connection.logout()
