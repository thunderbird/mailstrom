import datetime
import sys

from locust import constant, events, task

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.IMAP import IMAP
from common.logger import log

from MailstromUser import MailstromUser

from const import (
    TEST_SERVER_HOST,
    IMAP_PORT,
    CONNECT_TIMEOUT,
    LOAD_TEST_FOLDER_NAME_PREFIX,
)

GLOBAL_FAILED_SIGN_INS = []


class MailstromIMAPUser(MailstromUser):
    # each task is repeated over and over by each test user; wait N seconds after each task is run
    wait_time = constant(2)
    folder_count = 0
    connection = None
    test_user = None

    def on_start(self):
        # runs one time for each user (when the user is spun-up)
        self.folder_count = 0

        # each user instance grabs one unique test account/credentials
        self.test_user = self.get_next_user()
        log.debug(
            f'user instance {id(self)}: signing in to imap with username: {self.test_user["username"].split("@")[0]}'
        )

        self.connection = IMAP(TEST_SERVER_HOST, IMAP_PORT, CONNECT_TIMEOUT, locust=True)
        success = self.connection.login(self.test_user['username'], self.test_user['password'])
        if not success:
            # exit this user instance but locust test will continue with other users
            GLOBAL_FAILED_SIGN_INS.append(self.test_user['username'])
            raise Exception(f'imap sign-in failed for: {self.test_user["username"]} (user instance {id(self)})')

    @task
    # this task will be repeated over and over by each user (until the test run-time is met)
    def imap_create_folder(self):
        # create a folder (mailbox) in our LOAD_TEST_ACCT
        self.folder_count += 1
        log.debug(f'user instance {id(self)}: creating folder {self.folder_count} via imap')
        folder_name = (
            f'{LOAD_TEST_FOLDER_NAME_PREFIX} - User {id(self)} - Folder {self.folder_count} - {datetime.datetime.now()}'
        )
        self.connection.create_mailbox(folder_name)

        # now subscribe to the mailbox so we can view it in TB if we want to check results after
        self.connection.subscribe_mailbox(folder_name)

    def on_stop(self):
        # runs one time for each user (when the tests are finished )
        log.debug(f'user instance {id(self)}: signing out of imap')
        self.connection.logout()

    def on_quitting(environment, **kwargs):
        # runs one time when all test instances are done and locust is about to quit
        log.debug('locust tests complete!')
        if GLOBAL_FAILED_SIGN_INS:
            log.debug(
                f'***** These {len(GLOBAL_FAILED_SIGN_INS)} test users failed to sign-in to smtp '
                + '(please check credentials in your .load_test_users.csv): *****'
            )
            for user in GLOBAL_FAILED_SIGN_INS:
                log.debug(user)

    # register the event handler
    events.quitting.add_listener(on_quitting)
