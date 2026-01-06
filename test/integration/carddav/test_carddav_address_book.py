import time

from datetime import datetime
from urllib.parse import quote

from common.CardDAV import CardDAV

from common.const import (
    ADDRESS_BOOK_PREFIX,
    TEST_SLEEP_1_SECOND,
)

from const import (
    CARDDAV_EXP_DEFAULT_ADDRESS_BOOK_NAME,
    TEST_CARDDAV_URL,
    CONNECT_TIMEOUT,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


class TestCarddavAddressBook:
    def test_get_address_books(self, carddav):
        # get all of the address books, should be at least one
        abs_returned = carddav.get_address_books()
        assert len(abs_returned) > 0, 'expected at least 1 address book to exist'

    def test_get_default_address_book(self, carddav):
        # retrieve the default address book and verify
        default_ab = None
        all_abs = carddav.get_address_books()

        for ab in all_abs:
            if 'default' in ab['href']:
                default_ab = ab

        assert default_ab is not None, 'expected to be able to find the default address book'
        assert quote(carddav.username) in default_ab['href'], 'expected default address book url to be correct'
        # note: this currently fails, pending issue #63 being resolved
        assert default_ab['displayname'] == CARDDAV_EXP_DEFAULT_ADDRESS_BOOK_NAME, (
            'expected default address book name to be correct'
        )
        return

    def test_create_address_book(self, carddav):
        # create a new address book and verify
        ab_name = f'{ADDRESS_BOOK_PREFIX} {datetime.now()}'
        success = carddav.create_address_book(ab_name)
        assert success, 'expected to be able to create a new address book'

        # now verify new one actually exists
        time.sleep(TEST_SLEEP_1_SECOND)
        assert carddav.does_address_book_exist(ab_name), 'expected new address book to exist'

    def test_delete_address_book(self, carddav):
        # create a new address book, delete it, and verify
        ab_name = f'{ADDRESS_BOOK_PREFIX} {datetime.now()}'
        success = carddav.create_address_book(ab_name)
        assert success, 'expected to be able to create a new address book'

        # find the new address book and then delete it
        success = carddav.delete_address_book_by_name(ab_name)
        assert success, 'expected to be able to delete the address book'

        # now verify address book doesn't exist any more
        time.sleep(TEST_SLEEP_1_SECOND)
        assert carddav.does_address_book_exist(ab_name) is False, 'expected address book to not exist after deletion'

    def test_address_book_visible_multiple_clients(self, carddav):
        # add a new address book with one client, verify the ab is sync'd/seen with 2nd client
        # our first carddav client is the one provided by the fixture; we'll create a second one
        second_carddav_client = CardDAV(TEST_CARDDAV_URL, CONNECT_TIMEOUT)
        login_success = second_carddav_client.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert login_success, 'expected to be able to connect to carddav server with second client'

        # create a new address book with our first carddav client
        ab_name = f'{ADDRESS_BOOK_PREFIX} {datetime.now()}'
        success = carddav.create_address_book(ab_name)
        assert success, 'expected to be able to create a new address book with first carddav client'

        # now search for the new address book with the second carddav client, confirm is found
        time.sleep(TEST_SLEEP_1_SECOND)
        assert second_carddav_client.does_address_book_exist(ab_name), (
            'expected new address book to be seen by the second carddav client'
        )

        # delete the address book with the second carddav client
        success = second_carddav_client.delete_address_book_by_name(ab_name)
        assert success, 'expected to be able to delete the address book using the second carddav client'

        # now search for the address book with the first carddav client and it shouldn't be found
        time.sleep(TEST_SLEEP_1_SECOND)
        assert carddav.does_address_book_exist(ab_name) is False, 'expected address book to not exist after deletion'

        # done with our second client
        second_carddav_client.logout()
