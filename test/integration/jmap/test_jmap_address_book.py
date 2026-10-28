import datetime
import time

from common.JMAP import JMAP

from common.const import (
    ADDRESS_BOOK_PREFIX,
    TEST_SLEEP_1_SECOND,
)

from const import (
    TEST_SERVER_HOST,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


class TestJMAPAddressBook:
    def test_get_address_books(self, jmap_acct_1):
        # get all of the address books, should be at least one by default
        address_books = jmap_acct_1.get_address_books()
        assert len(address_books) > 0, 'expected at least one address book to already exist'

    def test_create_address_book(self, jmap_acct_1):
        # create a new address book and verify it exists; using the ADDRESS_BOOK_PREFIX ensures
        # that they will automatically be cleaned up (via conftest.py:cleanup_prev_test_data)
        ab_name = f'{ADDRESS_BOOK_PREFIX} JMAP {datetime.datetime.now()}'
        result = jmap_acct_1.create_address_book(ab_name)
        assert result, 'expected addressbook to have been created successfully'
        assert result['newAddressBook']['id'], 'expected addressbook id to have been returned'

        # get address books and verify our new one exists
        ab_id = result['newAddressBook']['id']
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found, 'expected address book to exist'
        assert abs_found['id'] == ab_id
        assert abs_found['name'] == ab_name

    def test_rename_address_book(self, jmap_acct_1):
        # create a new address book
        ab_name = f'{ADDRESS_BOOK_PREFIX} JMAP (rename me) {datetime.datetime.now()}'
        result = jmap_acct_1.create_address_book(ab_name)
        assert result, 'expected addressbook to have been created successfully'
        assert result['newAddressBook']['id'], 'expected addressbook id to have been returned'

        # get address books and verify our new one exists
        ab_id = result['newAddressBook']['id']
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found, 'expected address book to exist'
        assert abs_found['id'] == ab_id
        assert abs_found['name'] == ab_name

        # rename it
        new_ab_name = f'{ADDRESS_BOOK_PREFIX} JMAP (renamed!) {datetime.datetime.now()}'
        success = jmap_acct_1.rename_address_book(ab_id, new_ab_name)
        assert success, 'expected to be able to rename the address book'

        # get address books and verify name was changed
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found, 'expected address book to exist'
        assert abs_found['id'] == ab_id
        assert abs_found['name'] == new_ab_name, 'expected address book name to have been changed'

    def test_delete_empty_address_book(self, jmap_acct_1):
        # create a new empty address book, verify
        ab_name = f'{ADDRESS_BOOK_PREFIX} JMAP (empty) {datetime.datetime.now()}'
        result = jmap_acct_1.create_address_book(ab_name)
        assert result, 'expected addressbook to have been created successfully'
        assert result['newAddressBook']['id'], 'expected addressbook id to have been returned'

        # get address books and verify our new one exists
        ab_id = result['newAddressBook']['id']
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found, 'expected address book to exist'
        assert abs_found['id'] == ab_id
        assert abs_found['name'] == ab_name

        # delete it
        success = jmap_acct_1.delete_address_book_by_id(ab_id)
        assert success, 'expected to be able to delete the address book'

        # now verify address book doesn't exist any more
        time.sleep(TEST_SLEEP_1_SECOND)
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found is None, 'expected address book to no longer exist'

    def test_delete_non_empty_address_book(self, jmap_acct_1):
        # create a new empty address book
        ab_name = f'{ADDRESS_BOOK_PREFIX} JMAP (not empty) {datetime.datetime.now()}'
        result = jmap_acct_1.create_address_book(ab_name)
        assert result, 'expected addressbook to have been created successfully'
        assert result['newAddressBook']['id'], 'expected addressbook id to have been returned'

        # get address books and verify our new one exists
        ab_id = result['newAddressBook']['id']
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found, 'expected address book to exist'
        assert abs_found['id'] == ab_id
        assert abs_found['name'] == ab_name

        # add a contact to our new address book, verify
        contact_details = {
            'name': {
                'components': [{'kind': 'given', 'value': 'Some'}, {'kind': 'surname', 'value': 'Person'}],
                'isOrdered': True,
            },
            'emails': {
                '0': {'contexts': {'work': True}, 'address': 'someperson@example.org'},
            },
            'notes': {'n1': {'note': f'Created by integration tests at {datetime.datetime.now()}'}},
        }

        success = jmap_acct_1.create_contact(ab_id, contact_details)
        assert success, 'expected to be able to create a new contact in the address book'

        # attempt to delete the address book; onDestroyRemoveContents is false by default for new
        # address books, so attempting to delete a non-empty address book should result in err
        del_attempt = jmap_acct_1.delete_address_book_by_id(ab_id)

        assert del_attempt['notDestroyed'], 'expected error when attempt to delete non-empty adress book'
        assert del_attempt['notDestroyed'][ab_id]['description'] == 'Address book is not empty.'

        # now verify address book still exists
        time.sleep(TEST_SLEEP_1_SECOND)
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found, 'expected address book to still exist'
        assert abs_found['id'] == ab_id

    def test_address_book_visible_multiple_clients(self, jmap_acct_1):
        # add a new ab with one client, verify the ab is sync'd/seen with 2nd client for same account
        # our first client is the one provided by the fixture; we'll create a second one for same account
        jmap_acct_1_client_2 = JMAP(TEST_SERVER_HOST, TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert jmap_acct_1_client_2.client is not None, 'expected jmap client'

        # create a new address book with our first jmap client
        ab_name = f'{ADDRESS_BOOK_PREFIX} JMAP {datetime.datetime.now()}'
        result = jmap_acct_1.create_address_book(ab_name)
        assert result, 'expected addressbook to have been created successfully'
        assert result['newAddressBook']['id'], 'expected addressbook id to have been returned'

        # now search for the new address book with the second jmap client, confirm is found
        ab_id = result['newAddressBook']['id']
        abs_found = jmap_acct_1_client_2.get_address_book_by_id(ab_id)
        assert abs_found, 'expected address book to be seen by the second jmap client'
        assert abs_found['id'] == ab_id
        assert abs_found['name'] == ab_name

        # delete the address book with the second jmap client
        success = jmap_acct_1_client_2.delete_address_book_by_id(ab_id)
        assert success, 'expected to be able to delete the address book using the second jmap client'

        # now search for the address book with the first jmap client and it shouldn't be found
        abs_found = jmap_acct_1.get_address_book_by_id(ab_id)
        assert abs_found is None, 'expected address book to no longer be seen by the first jmap client'
