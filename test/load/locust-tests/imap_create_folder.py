import datetime
import logging
import sys
from locust import User, constant, task

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.IMAP import IMAP

from const import (
    TEST_SERVER_HOST,
    IMAP_PORT,
    CONNECT_TIMEOUT,
    LOAD_TEST_ACCT_USERNAME,
    LOAD_TEST_ACCT_PASSWORD,
    LOAD_TEST_FOLDER_NAME_PREFIX,
)


class MailstromIMAPUser(User):
    # each task is repeated over and over by each test user; wait N seconds after each task is run
    # with 3 seconds wait, each user will create approximately 20 folders per minute when all spawned
    wait_time = constant(3)
    folder_count = 0
    connection = None

    def on_start(self):
        # runs one time for each user (when the user is spun-up)
        self.folder_count = 0
        logging.debug(f'user instance {id(self)}: signing in to imap')
        self.connection = IMAP(TEST_SERVER_HOST, IMAP_PORT, CONNECT_TIMEOUT)
        success = self.connection.login(LOAD_TEST_ACCT_USERNAME, LOAD_TEST_ACCT_PASSWORD)
        assert success, 'expected imap login to be successful'

    @task
    # this task will be repeated over and over by each user (until the test run-time is met)
    def imap_create_folder(self):
        # create a folder (mailbox) in our LOAD_TEST_ACCT
        self.folder_count += 1
        logging.debug(f'user instance {id(self)}: creating folder {self.folder_count} via imap')
        folder_name = (
            f'{LOAD_TEST_FOLDER_NAME_PREFIX} - User {id(self)} - Folder {self.folder_count} - {datetime.datetime.now()}'
        )
        self.connection.create_mailbox(folder_name, locust=True)

        # now subscribe to the mailbox so we can view it in TB if we want to check results after
        self.connection.subscribe_mailbox(folder_name, locust=True)

    def on_stop(self):
        # runs one time for each user (when the tests are finished )
        logging.debug(f'user instance {id(self)}: signing out of imap')
        self.connection.logout()
