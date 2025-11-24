import sys

from datetime import datetime
from faker import Faker
from locust import constant, events, task

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.CardDAV import CardDAV
from common.logger import log

from const import (
    CONNECT_TIMEOUT,
    TEST_CARDDAV_URL,
    LOAD_TEST_ADDRESS_BOOK_NAME_PREFIX,
)

from MailstromUser import MailstromUser

GLOBAL_FAILED_SIGN_INS = []


class MailstromCarddavUser(MailstromUser):
    # each task is repeated over and over by each test user; wait N seconds after each task is run
    wait_time = constant(2)
    folder_count = 0
    connection = None
    test_user = None
    test_address_book = None
    fake = None

    def on_start(self):
        # runs one time for each user (when the user is spun-up)
        self.contacts_count = 0
        self.fake = Faker()

        # each user instance grabs one unique test account/credentials
        self.test_user = self.get_next_user()
        log.debug(
            f'user instance {id(self)}: signing in to imap with username: {self.test_user["username"].split("@")[0]}'
        )

        self.connection = CardDAV(TEST_CARDDAV_URL, CONNECT_TIMEOUT, locust=True)
        login_success = self.connection.login(self.test_user['username'], self.test_user['password'])

        if not login_success:
            # exit this user instance but locust test will continue with other users
            GLOBAL_FAILED_SIGN_INS.append(self.test_user['username'])
            raise Exception(f'carddav sign-in failed for: {self.test_user["username"]} (user instance {id(self)})')

        # now create a test address book to be used to add contacts to
        ab_name = f'{LOAD_TEST_ADDRESS_BOOK_NAME_PREFIX} created {datetime.now()}'
        ab_success = self.connection.create_address_book(ab_name)
        if ab_success:
            self.test_address_book = self.connection.get_address_book_by_name(ab_name)

        if self.test_address_book is None:
            # exit this user instance but locust test will continue with other users
            raise Exception(
                f'failed to create new address book for user: {self.test_user["username"]} (user instance {id(self)})'
            )

    @task
    # this task will be repeated over and over by each user (until the test run-time is met)
    def carddav_create_contact(self):
        # create a contact in our load test address book
        self.contacts_count += 1
        log.debug(f'user instance {id(self)}: creating contact {self.contacts_count} via carddav')

        # now create a contact in our new test address book so it's not empty
        first = self.fake.first_name()
        last = self.fake.last_name()
        full = f'{first} {last}'
        cell = self.fake.phone_number()
        email = f'fake-email-{first}-{last}@example.org'

        contact_details = {
            'first_name': first,
            'last_name': last,
            'full_name': full,
            'cell': cell,
            'email': email,
        }
        self.connection.create_contact(self.test_address_book['href'], contact_details)

    def on_stop(self):
        # runs one time for each user (when the tests are finished )
        log.debug(f'user instance {id(self)}: signing out of carddav')
        self.connection.logout()

    def on_quitting(environment, **kwargs):
        # runs one time when all test instances are done and locust is about to quit
        log.debug('locust tests complete!')
        if GLOBAL_FAILED_SIGN_INS:
            log.debug(
                f'***** These {len(GLOBAL_FAILED_SIGN_INS)} test users failed to sign-in to carddav '
                + '(please check credentials in your .load_test_users.csv): *****'
            )
            for user in GLOBAL_FAILED_SIGN_INS:
                log.debug(user)

    # register the event handler
    events.quitting.add_listener(on_quitting)
