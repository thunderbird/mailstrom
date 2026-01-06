import datetime
import sys
from locust import constant, events, task

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.JMAP import JMAP
from common.logger import log

from MailstromUser import MailstromUser

from const import (
    TEST_SERVER_HOST,
    LOAD_TEST_TO_EMAIL,
    LOAD_TEST_EMAIL_SUBJECT_PREFIX,
)

from common.const import (
    TEST_MSG_BODY_PREFIX,
)

GLOBAL_FAILED_SIGN_INS = []


class MailstromJMAPUser(MailstromUser):
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

        log.debug(
            f'user instance {id(self)}: signing in to jmap with username: {self.test_user["username"].split("@")[0]}'
        )
        try:
            self.connection = JMAP(
                TEST_SERVER_HOST, self.test_user['username'], self.test_user['password'], locust=True
            )

            assert self.connection.client is not None, 'expected jmap client'

        except Exception:
            # exit this user instance but locust test will continue with other users
            GLOBAL_FAILED_SIGN_INS.append(self.test_user['username'])
            raise Exception(f'jmap sign-in failed for: {self.test_user["username"]} (user instance {id(self)})')

    @task
    # this task will be repeated over and over by each user (until the test run-time is met)
    def jmap_send_email(self):
        # send email via jmap from our load test account
        self.email_count += 1

        log.debug(
            f'user instance {id(self)} {self.test_user["username"].split("@")[0]}: sending email message '
            + f'{self.email_count} via jmap'
        )
        subject = (
            f'{LOAD_TEST_EMAIL_SUBJECT_PREFIX} (user instance {id(self)} '
            + f'msg {self.email_count}) {datetime.datetime.now()}'
        )

        self.connection.send_email(
            from_email=self.test_user['email'],
            to_email=LOAD_TEST_TO_EMAIL,
            subject=subject,
            plain_text_body=TEST_MSG_BODY_PREFIX,
        )

    def on_stop(self):
        # runs one time for each user (when the tests are finished )
        log.debug('user instance is finished')

    def on_quitting(environment, **kwargs):
        # runs one time when all test instances are done and locust is about to quit
        log.debug('locust tests complete!')
        if GLOBAL_FAILED_SIGN_INS:
            log.debug(
                f'***** These {len(GLOBAL_FAILED_SIGN_INS)} test users failed to connect to jmap '
                + '(please check credentials in your .load_test_users.csv): *****'
            )
            for user in GLOBAL_FAILED_SIGN_INS:
                log.debug(user)

    # register the event handler
    events.quitting.add_listener(on_quitting)
