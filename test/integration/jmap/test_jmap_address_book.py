import datetime


from common.const import (
    ADDRESS_BOOK_PREFIX,
)


class TestJMAPAddressBook:
    def test_get_address_books(self, carddav):
        # get all of the address books, should be at least one
        assert True

    def test_create_address_book(self, jmap_acct_1):
        # create a new address book and verify it exists; using the ADDRESS_BOOK_PREFIX ensures
        # that they will automatically be cleaned up (via conftest.py:cleanup_prev_test_data)
        ab_name = f'{ADDRESS_BOOK_PREFIX} JMAP {datetime.datetime.now()}'
        result = jmap_acct_1.create_addressbook(ab_name)
        assert result, 'expected addressbook to have been created successfully'
        assert result['newAddressBook']['id'], 'expected addressbook id to have been returned'

        # get address books and verify our new one exists
        # todo

    def test_delete_address_book(self, carddav):
        # create a new address book, delete it, and verify
        # todo    

        # find the new address book and then delete it
        # todo

        # now verify address book doesn't exist any more
        #time.sleep(TEST_SLEEP_1_SECOND)
        # todo
        assert True

    def test_address_book_visible_multiple_clients(self, carddav):
        # add a new address book with one client, verify the ab is sync'd/seen with 2nd client
        # our first carddav client is the one provided by the fixture; we'll create a second one

        # create a new address book with our first carddav client
        # todo

        # now search for the new address book with the second carddav client, confirm is found
        # todo

        # delete the address book with the second carddav client
        # todo

        # now search for the address book with the first carddav client and it shouldn't be found
        #time.sleep(TEST_SLEEP_1_SECOND)
        # todo

        # done with our second client, logout

        assert True
