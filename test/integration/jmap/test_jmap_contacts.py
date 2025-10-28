import datetime
import pytest
import time

from common.const import (
    TEST_SLEEP_1_SECOND,
)


class TestJMAPContacts:
    # build a list of contacts that we want to test creating
    test_contacts = [
        {
            'name': {
                'components': [{'kind': 'given', 'value': 'James'}, {'kind': 'surname', 'value': 'Bond'}],
                'isOrdered': True,
            },
            'emails': {
                '0': {'contexts': {'work': True}, 'address': 'jamesbond@example.org'},
            },
        },
        {
            'name': {
                'components': [{'kind': 'given', 'value': 'Jane'}, {'kind': 'surname', 'value': 'Bond'}],
                'isOrdered': True,
            },
            'emails': {
                '0': {'contexts': {'private': True}, 'address': 'janebond-home@example.org'},
                '1': {'contexts': {'work': True}, 'address': 'janebond-work@example.org'},
                '2': {'contexts': {'other': True}, 'address': 'janebond-other@example.org'},
                '3': {
                    'contexts': {'custom': True},
                    'label': 'Custom email label',
                    'address': 'janebond-custom@example.org',
                },
            },
        },
        {
            'name': {
                'components': [{'kind': 'given', 'value': 'Firstname'}, {'kind': 'surname', 'value': 'Lastname'}],
                'isOrdered': True,
            },
            'emails': {
                '0': {'contexts': {'work': True}, 'address': 'firstnamelastname@example.org'},
            },
            'notes': {'n1': {'note': f'Created by integration tests at {datetime.datetime.now()}'}},
        },
    ]

    def test_get_contacts(self, jmap_acct_1, test_address_book_jmap):
        # get all of the contacts in our test address book (test_address_book with one contact
        # was already created in our conftest test_address_book_jmap fixture)
        all_contacts = jmap_acct_1.get_contacts(test_address_book_jmap['id'])
        assert all_contacts, 'expected at least one contact to exist'

    @pytest.mark.parametrize('contact_details', test_contacts)
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
        assert ret_contact['name']['components'] == contact_details['name']['components'], (
            'expected new contact name to be correct'
        )
        assert ret_contact['emails'] == contact_details['emails'], 'expected new contact email(s) to be correct'

        if contact_details.get('notes', None):
            assert ret_contact['notes'] == contact_details['notes'], 'expected new contact notes to be correct'

        # todo add another test contact will all the available fields used, verify
