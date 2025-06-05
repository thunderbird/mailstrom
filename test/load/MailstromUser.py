import csv
import sys

from locust import User

# since we are calling locust cmd line we need to add common to path
sys.path.append('../')
from common.logger import log

from const import (
    LOAD_TEST_USERS_CSV,
)

# one global list of test user credentials shared by all instances
USER_CREDENTIALS = None


"""
MailstromUser class, use this as our base clase for every load test. Inherits from locust User.
Enables reading mailstrom test account credentials from the local credentials CSV file, and
provide the credentials to the load tests. Each locust load test user instance will use one
unique test account and associated credentials from the local credentials file.
"""


class MailstromUser(User):
    # must set this since we are inheriting the locust User base class but not providing
    # an actual locust task here; the task will be provided in our subclass that inherits this
    abstract = True

    def __init__(self, environment):
        # read our user credentials from the local credentials file (NOT in the repo!); reading from the
        # the credentials file will only happen one time (when the very first user spins up)
        super().__init__(environment)

        global USER_CREDENTIALS
        if USER_CREDENTIALS is None:
            USER_CREDENTIALS = []
            log.debug('reading load test user credentials from local csv file')

            try:
                with open(LOAD_TEST_USERS_CSV, newline='') as creds_csv:
                    reader = csv.reader(creds_csv)
                    for cred in reader:
                        USER_CREDENTIALS.append(
                            {
                                'username': cred[0],
                                'password': cred[1],
                                'email': cred[2],
                            }
                        )

            except FileNotFoundError:
                raise Exception('local credentials file not found!')

    def get_next_user(self):
        # return the next user from our credentials list, remove it from the list so that
        # no other user instance will use the same credentials
        if len(USER_CREDENTIALS) > 0:
            return USER_CREDENTIALS.pop()
        else:
            # exit this user instance but locust test will continue with other users
            raise Exception('attempting to spin up new user but ran out of credentials in credentials file')
