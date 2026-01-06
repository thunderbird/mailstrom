import pytest
import time

from common.const import (
    TEST_SLEEP_1_SECOND,
)


class TestCarddavContacts:
    # build a list of contacts that we want to test creating
    test_contacts = [
        {
            'first_name': 'John',
            'last_name': 'Doe',
            'full_name': 'Mr. John Doe',
            'email_home': 'fake-email-johndoe@example.org',
        },
        {
            'first_name': 'Jane',
            'last_name': 'Doe',
            'full_name': 'Mrs. Jane Doe',
            'email_home': 'fake-email-janedoe@example.org',
            'tel_cell': '15551234567',
        },
        {
            'first_name': 'James',
            'last_name': 'Bond',
            'full_name': 'Bond, James Bond',
            'tel_cell': '15550000000',
            'tel_work': '15550070070',
            'email_home': 'fake-email-james@example.org',
            'email_work': 'fake-email-jbond@example.org',
            'nickname': '007',
            'address': {
                'street': '123 Spy Street East',
                'city': 'London',
                'region': 'SW',
                'code': 'SW1A 1AA',
                'country': 'United Kingdom',
            },
            'note': 'Fav drink is a Martini!',
            'website': 'https://en.wikipedia.org/wiki/James_Bond',
        },
        {
            'first_name': 'Thunderbird',
            'last_name': 'Pro',
            'full_name': 'Thunderbird Pro!',
            'website': 'https://www.tb.pro',
            'note': 'Sign up for TB Pro today!',
            'email_work': 'support@tb.pro',
        },
    ]

    @pytest.mark.parametrize('contact_details', test_contacts)
    def test_create_contact(self, carddav, test_address_book, contact_details):
        # create a new contact in our test address book and verify; before the tests started
        # a test address book was created (see the test_addresss_book fixture in conftest.py)
        success = carddav.create_contact(test_address_book['href'], contact_details)
        assert success, 'expected to be able to create a new contact'

        # get the new contact and verify details
        time.sleep(TEST_SLEEP_1_SECOND)

        contact_name = f'{contact_details["first_name"].lower()}-{contact_details["last_name"].lower()}'
        contact_href = f'{test_address_book["href"]}{contact_name}.vcf'
        found_vcard = carddav.get_contact_details(contact_href)

        # now verify contact values are correct
        assert found_vcard is not None, 'expected to be able to retrieve contact details'
        assert found_vcard.n.value.given == contact_details['first_name'], 'expected first name to be correct'
        assert found_vcard.n.value.family == contact_details['last_name'], 'expected first name to be correct'
        assert found_vcard.fn.value == contact_details['full_name'], 'expected full name to be correct'

        if contact_details.get('tel_cell'):
            found_tel = None
            for tel in found_vcard.tel_list:
                if tel.type_param.lower() == 'cell':
                    found_tel = tel.value
            assert found_tel == contact_details['tel_cell'], 'expected cell tel to be correct'

        if contact_details.get('tel_work'):
            found_tel = None
            for tel in found_vcard.tel_list:
                if tel.type_param.lower() == 'work':
                    found_tel = tel.value
            assert found_tel == contact_details['tel_work'], 'expected work tel to be correct'

        if contact_details.get('email_home'):
            found_email = None
            for email in found_vcard.email_list:
                if email.type_param.lower() == 'home':
                    found_email = email.value
            assert found_email == contact_details['email_home'], 'expected home email to be correct'

        if contact_details.get('email_work'):
            found_email = None
            for email in found_vcard.email_list:
                if email.type_param.lower() == 'work':
                    found_email = email.value
            assert found_email == contact_details['email_work'], 'expected work email to be correct'

        if contact_details.get('nickname'):
            assert found_vcard.nickname.value == contact_details['nickname'], 'expected nickname to be correct'

        if contact_details.get('address'):
            assert found_vcard.adr.type_param == 'HOME', 'expected address type to be correct'
            assert found_vcard.adr.value.street == contact_details['address']['street'], 'expected street to be correct'
            assert found_vcard.adr.value.city == contact_details['address']['city'], 'expected city to be correct'
            assert found_vcard.adr.value.region == contact_details['address']['region'], 'expected region to be correct'
            assert found_vcard.adr.value.code == contact_details['address']['code'], 'expected postcode to be correct'
            assert found_vcard.adr.value.country == contact_details['address']['country'], (
                'expected country to be correct'
            )

        if contact_details.get('website'):
            assert found_vcard.url.value == contact_details['website'], 'expected nickname to be correct'
            assert found_vcard.url.type_param == 'WEBSITE', 'expected website type to be correct'

        if contact_details.get('note'):
            assert found_vcard.note.value == contact_details['note'], 'expected note to be correct'

    def test_get_contacts_list(self, carddav, test_address_book):
        # retrieve a list of all of the contacts that exist in our test address book; we know there
        # is at least one because when our test address book was created one contact was added
        all_contacts = carddav.get_all_contacts(test_address_book['href'])
        assert all_contacts is not None, 'expected at least one contact to be found'

    def test_update_contact(self, carddav, test_address_book):
        # edit an existing contact and verify changes were saved; we know at least one contact already
        # exists in our test address book that was created at the test start by our conftest.py fixture
        all_contacts = carddav.get_all_contacts(test_address_book['href'])
        assert all_contacts is not None, 'expected at least one contact to be found'

        # retrieve the existing contact details (vCard)
        contact_href = all_contacts[0]
        contact_vcard = carddav.get_contact_details(contact_href)

        # now modify the vCard locally (display name)
        new_fn = 'New modified display name!'
        contact_vcard.fn.value = new_fn

        # submit the modified vCard to save the changes
        carddav.update_contact(test_address_book['href'], contact_href, contact_vcard)
        time.sleep(TEST_SLEEP_1_SECOND)

        # now retrieve the contact details again and verify it was updated correctly
        latest_contact_vcard = carddav.get_contact_details(contact_href)
        assert latest_contact_vcard.fn.value == new_fn, 'expected contact full name to have been updated correctly'

    def test_delete_contact(self, carddav, test_address_book):
        # create a new contact, delete it and verify
        contact_data = {
            'first_name': 'Delete',
            'last_name': 'This',
            'full_name': 'Delete this contact!',
            'email_home': 'fake-email-delete-this-contact@example.org',
            'tel_cell': '15550000000',
        }

        success = carddav.create_contact(test_address_book['href'], contact_data)
        assert success, 'expected to be able to create a new contact'

        # verify new contact exists
        time.sleep(TEST_SLEEP_1_SECOND)
        contact_name = f'{contact_data["first_name"].lower()}-{contact_data["last_name"].lower()}'
        contact_href = f'{test_address_book["href"]}{contact_name}.vcf'
        found_vcard = carddav.get_contact_details(contact_href)
        assert found_vcard is not None, 'expected to be able to find newly created contact'

        # now delete the contact
        carddav.delete_contact_by_href(contact_href)

        # and verify it no longer exists
        found_vcard = carddav.get_contact_details(contact_href)
        assert found_vcard is None, 'expected NOT to be able to find contact after it was deleted'
