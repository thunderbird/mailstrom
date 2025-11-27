import pytz
import sys

from datetime import datetime, timedelta

from locust import constant, events, task

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.CalDAV import CalDAV
from common.logger import log

from const import (
    CONNECT_TIMEOUT,
    TEST_CALDAV_URL,
    LOAD_TEST_CALENDAR_NAME_PREFIX,
    LOAD_TEST_EVENT_NAME_PREFIX,
)

from MailstromUser import MailstromUser

GLOBAL_FAILED_SIGN_INS = []


class MailstromCaldavUser(MailstromUser):
    # each task is repeated over and over by each test user; wait N seconds after each task is run
    wait_time = constant(2)
    folder_count = 0
    connection = None
    test_user = None
    test_calendar = None

    def on_start(self):
        # runs one time for each user (when the user is spun-up)
        self.event_count = 0

        # each user instance grabs one unique test account/credentials
        self.test_user = self.get_next_user()
        log.debug(
            f'user instance {id(self)}: signing in to caldav with username: {self.test_user["username"].split("@")[0]}'
        )

        self.connection = CalDAV(TEST_CALDAV_URL, CONNECT_TIMEOUT, locust=True)
        login_success = self.connection.login(self.test_user['username'], self.test_user['password'])

        if not login_success:
            # exit this user instance but locust test will continue with other users
            GLOBAL_FAILED_SIGN_INS.append(self.test_user['username'])
            raise Exception(f'caldav sign-in failed for: {self.test_user["username"]} (user instance {id(self)})')

        # now create a test calendar in this user's account, to be used to add events to
        self.test_calendar = self.connection.make_calendar(f'{LOAD_TEST_CALENDAR_NAME_PREFIX} created {datetime.now()}')
        if not self.test_calendar:
            # exit this user instance but locust test will continue with other users
            raise Exception(
                f'failed to create new calendar for user: {self.test_user["username"]} (user instance {id(self)})'
            )

    @task
    # this task will be repeated over and over by each user (until the test run-time is met)
    def caldav_create_event(self):
        # create an event in our load test calendar
        self.event_count += 1
        log.debug(f'user instance {id(self)}: creating event {self.event_count} via caldav')

        tz_tor = pytz.timezone('America/Toronto')
        event_start = datetime.now(tz=tz_tor) + timedelta(minutes=5)
        event_end = event_start + timedelta(minutes=5)

        event_props = {
            'dtstart': event_start,
            'dtend': event_end,
            'summary': f'{LOAD_TEST_EVENT_NAME_PREFIX} created {datetime.now()}',
        }
        self.connection.create_event(self.test_calendar, event_props)

    def on_stop(self):
        # runs one time for each user (when the tests are finished )
        log.debug(f'user instance {id(self)}: signing out of caldav')
        self.connection.logout()

    def on_quitting(environment, **kwargs):
        # runs one time when all test instances are done and locust is about to quit
        log.debug('locust tests complete!')
        if GLOBAL_FAILED_SIGN_INS:
            log.debug(
                f'***** These {len(GLOBAL_FAILED_SIGN_INS)} test users failed to sign-in to caldav '
                + '(please check credentials in your .load_test_users.csv): *****'
            )
            for user in GLOBAL_FAILED_SIGN_INS:
                log.debug(user)

    # register the event handler
    events.quitting.add_listener(on_quitting)
