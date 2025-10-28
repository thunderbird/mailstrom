import pytest
import time

from common.JMAP import JMAP

from common.const import (
    TEST_SLEEP_1_SECOND,
)

from const import (
    TEST_SERVER_HOST,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)

from integration.jmap.contacts_data import (
    JMAP_TEST_ADD_CONTACTS,
    JMAP_TEST_EDIT_CONTACT,
    JMAP_TEST_DELETE_CONTACT,
    JMAP_TEST_MULTI_CLIENT_CONTACT,
)


class TestJMAPContacts:
    def test_get_contacts(self, jmap_acct_1, test_address_book_jmap):
        # get all of the contacts in our test address book (test_address_book with one contact
        # was already created in our conftest test_address_book_jmap fixture)
        all_contacts = jmap_acct_1.get_contacts(test_address_book_jmap['id'])
        assert all_contacts, 'expected at least one contact to exist'

    @pytest.mark.parametrize('contact_details', JMAP_TEST_ADD_CONTACTS)
    def test_create_contact(self, jmap_acct_1, test_address_book_jmap, contact_details):
        # create a new contact in our test address book with the given contact_details and verify;
        # before the tests started a test ab was created (test_addresss_book fixture in conftest.py)
        ab_id = test_address_book_jmap['id']
        new_contact = jmap_acct_1.create_contact(ab_id, contact_details)
        assert new_contact, 'expected to be able to create a new contact'

        # get the new contact and verify details
        time.sleep(TEST_SLEEP_1_SECOND)

        # now verify contact values are correct
        ret_contact = jmap_acct_1.get_contact_by_id(ab_id, new_contact['newContactCard']['id'])
        assert ret_contact, 'expected contact to have been found'

        # we provided name as full name (one field) or in part
        if contact_details.get('name', {}).get('full'):
            assert ret_contact['name']['full'] == contact_details['name']['full'], (
                'expected new contact full name to be correct'
            )
        else:
            assert ret_contact['name']['components'] == contact_details['name']['components'], (
                'expected new contact first and last name to be correct'
            )

        if contact_details.get('emails'):
            assert ret_contact['emails'] == contact_details['emails'], 'expected new contact email(s) to be correct'

        if contact_details.get('notes'):
            assert ret_contact['notes'] == contact_details['notes'], 'expected new contact notes to be correct'

        # verify all other fields
        if contact_details.get('organizations'):
            assert ret_contact['organizations'] == contact_details['organizations'], (
                'expected new contact work org and dept to be correct'
            )

        if contact_details.get('titles'):
            assert ret_contact['titles'] == contact_details['titles'], 'expected new contact job title to be correct'

        if contact_details.get('links'):
            assert ret_contact['links'] == contact_details['links'], 'expected new contact website info to be correct'

    def test_edit_contact(self, jmap_acct_1, test_address_book_jmap):
        # create a new contact in our test address book with the given contact_details
        ab_id = test_address_book_jmap['id']
        new_contact = jmap_acct_1.create_contact(ab_id, JMAP_TEST_EDIT_CONTACT)
        assert new_contact, 'expected to be able to create a new contact'

        # get the new contact and verify details
        time.sleep(TEST_SLEEP_1_SECOND)

        ret_contact = jmap_acct_1.get_contact_by_id(ab_id, new_contact['newContactCard']['id'])
        assert ret_contact, 'expected contact to have been found'

        # we provided name as full name (one field) or in part
        if JMAP_TEST_EDIT_CONTACT.get('name', {}).get('full'):
            assert ret_contact['name']['full'] == JMAP_TEST_EDIT_CONTACT['name']['full'], (
                'expected new contact full name to be correct'
            )
        else:
            assert ret_contact['name']['components'] == JMAP_TEST_EDIT_CONTACT['name']['components'], (
                'expected new contact first and last name to be correct'
            )

        assert ret_contact['emails'] == JMAP_TEST_EDIT_CONTACT['emails'], 'expected new contact email to be correct'

        # edit the contact's email
        JMAP_TEST_EDIT_CONTACT['emails'] = {'0': {'address': 'superman@metropolis.com', 'contexts': {'work': True}}}
        updated_contact = jmap_acct_1.update_contact(new_contact['newContactCard']['id'], JMAP_TEST_EDIT_CONTACT)
        assert updated_contact, 'expected to be able to create a new contact'

        # get the contact and verify it was changed
        ret_contact = jmap_acct_1.get_contact_by_id(ab_id, new_contact['newContactCard']['id'])
        assert ret_contact, 'expected contact to have been found'

        # we provided name as full name (one field) or in part
        if JMAP_TEST_EDIT_CONTACT.get('name', {}).get('full'):
            assert ret_contact['name']['full'] == JMAP_TEST_EDIT_CONTACT['name']['full'], (
                'expected new contact full name to be correct'
            )
        else:
            assert ret_contact['name']['components'] == JMAP_TEST_EDIT_CONTACT['name']['components'], (
                'expected new contact first and last name to be correct'
            )

        assert ret_contact['emails'] == JMAP_TEST_EDIT_CONTACT['emails'], (
            'expected updated contact details to be correct'
        )

    def test_delete_contact(self, jmap_acct_1, test_address_book_jmap):
        # create a new contact in our test address book with the given contact_details
        ab_id = test_address_book_jmap['id']
        new_contact = jmap_acct_1.create_contact(ab_id, JMAP_TEST_DELETE_CONTACT)
        assert new_contact, 'expected to be able to create a new contact'

        # get the new contact and verify details
        time.sleep(TEST_SLEEP_1_SECOND)

        # now verify contact exists
        ret_contact = jmap_acct_1.get_contact_by_id(ab_id, new_contact['newContactCard']['id'])
        assert ret_contact, 'expected contact to have been found'
        assert ret_contact['emails'] == JMAP_TEST_DELETE_CONTACT['emails'], 'expected contact email to be correct'

        # delete the contact
        del_attempt = jmap_acct_1.delete_contact_by_id(new_contact['newContactCard']['id'])
        assert del_attempt.get('destroyed', [])[0] == new_contact['newContactCard']['id']

        # verify it no longer exists
        ret_contact = jmap_acct_1.get_contact_by_id(ab_id, new_contact['newContactCard']['id'])
        assert ret_contact is None, 'expected contact to no longer exist'

    def test_address_book_visible_multiple_clients(self, jmap_acct_1, test_address_book_jmap):
        # add a new contact with one client, verify contact is sync'd/seen with 2nd client for same account
        # our first client is the one provided by the fixture; we'll create a second one for same account
        jmap_acct_1_client_2 = JMAP(TEST_SERVER_HOST, TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert jmap_acct_1_client_2.client is not None, 'expected jmap client'

        # create a new contact with our first jmap client
        ab_id = test_address_book_jmap['id']
        new_contact = jmap_acct_1.create_contact(ab_id, JMAP_TEST_MULTI_CLIENT_CONTACT)
        assert new_contact, 'expected to be able to create a new contact'

        # get the new contact and verify details
        time.sleep(TEST_SLEEP_1_SECOND)

        # now verify contact exists
        ret_contact = jmap_acct_1.get_contact_by_id(ab_id, new_contact['newContactCard']['id'])
        assert ret_contact, 'expected contact to have been found'
        assert ret_contact['emails'] == JMAP_TEST_MULTI_CLIENT_CONTACT['emails'], 'expected contact email to be correct'

        # delete the contact with the second jmap client
        del_attempt = jmap_acct_1_client_2.delete_contact_by_id(new_contact['newContactCard']['id'])
        assert del_attempt.get('destroyed', [])[0] == new_contact['newContactCard']['id']

        # now search for the contact with the first jmap client and it shouldn't be found
        ret_contact = jmap_acct_1.get_contact_by_id(ab_id, new_contact['newContactCard']['id'])
        assert ret_contact is None, 'expected contact to no longer exist'
