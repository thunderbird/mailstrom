import datetime


from common.const import (
    ADDRESSBOOK_PREFIX,
)


class TestJMAPContacts:
    def test_create_addressbook(self, jmap_acct_1):
        # create a new address book and verify it exists
        name = f'{ADDRESSBOOK_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_addressbook(name)
        assert result, 'expected addressbook to have been created successfully'
        assert result['newAddressBook']['id'], 'expected addressbook id to have been returned'

        # get address books and verify our new one exists
        # todo
