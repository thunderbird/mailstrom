from imaplib import IMAP4_SSL
from const import IMAP_HOST, IMAP_PORT, RESULT_OK, STATE_NONAUTH, STATE_AUTH, STATE_LOGOUT, MAILBOX_SUBSCRIBED, \
    MAILBOX_CREATED, MAILBOX_DELETED, MAILBOX_UNSUBSCRIBED, LOGOUT_BYE, MAILBOX_PREFIX, MAILBOX_RENAMED, STATE_SELECTED, \
    STATE_AUTH, MAILBOX_CLOSE_COMPLETED
from utils import convert_raw_mailbox_list


class IMAP():
    def __init__(self):
        self.connection = None

    def login(self, username, password):
        """
        Connect and log into the IMAP server as defined in the .env.test file.
        """
        success = False
        print(f'\nconnecting to {IMAP_HOST}')

        try:
            self.connection = IMAP4_SSL(IMAP_HOST, IMAP_PORT)
            if self.connection.state == STATE_NONAUTH:
                print('connected, now signing in')
                self.connection.login(username, password)
                if self.connection.state == STATE_AUTH:
                    success = True
                    print(f'successfully signed into {IMAP_HOST}')

        except Exception as e:
            print(str(e))

        return success

    def logout(self):
        """
        Log out of the IMAP server.
        """
        if self.connection is not None and self.connection.state != STATE_LOGOUT:
            print(f'\nlogging out of {IMAP_HOST}')

            try:
                resp = IMAP4_SSL.logout(self.connection)
            except Exception as e:
                print(str(e))

            if LOGOUT_BYE in resp and self.connection.state == STATE_LOGOUT:
                print(f'successfullly signed out of {IMAP_HOST}')
                return True
        else:
            print('logout called however you are not currenty logged in')
        return False

    def get_capabilities(self):
        """
        Retrieve the list of IMAP server capabilities.
        """
        status = None
        capabilities = None

        if self.connection is not None and self.connection.state == STATE_AUTH:
            print('requesting IMAP server capabilities')
            status, raw_capabilities = IMAP4_SSL.capability(self.connection)
            capabilities = raw_capabilities[0].decode().split()
        else:
            print('unable to retrieve capabilities (not logged in to IMAP server)')
        return status, capabilities

    def get_mailboxes(self, subscribed_only=False):
        """
        Retrieve the list of mailboxes and return in a useful format.
        """
        if not subscribed_only:
            print('retrieving list of mailboxes')
            status, raw_data = self.connection.list()
        else:
            print('retrieving list of subscribed mailboxes')
            status, raw_data = self.connection.lsub()

        assert status == RESULT_OK, 'expected list to return OK'
        assert raw_data, 'expected list of mailboxes to be returned'

        # if any mailboxes found send back useful list
        if raw_data[0] is None:
            print('no mailboxes found')
            return []

        print(f'found {len(raw_data)} mailboxes')

        return convert_raw_mailbox_list(raw_data)

    def create_mailbox(self, name):
        """
        Create a new mailbox with the given name.
        """
        print(f'creating mailbox: {name}')
        status, data = self.connection.create(f'"{name}"') # need double quotes b/c spaces in name
        print(status, data)
        assert status == RESULT_OK, 'expected create to return OK'
        assert MAILBOX_CREATED in data[0], 'expected mailbox created message'

    def subscribe_mailbox(self, name):
        """
        Subscribe to the given mailbox. Need to do this so the mailbox appears in some clients like Thunderbird.
        """
        print(f'subscribing to mailbox: {name}')
        status, data = self.connection.subscribe(f'"{name}"')
        print(status, data)
        assert status == RESULT_OK, 'expected subscribe to return OK'
        assert MAILBOX_SUBSCRIBED in data[0], 'expected mailbox subscribed message'

    def unsubscribe_mailbox(self, name):
        """
        Unsubscribe the given mailbox.
        """
        print(f'unsubscribing to mailbox: {name}')
        status, data = self.connection.unsubscribe(f'"{name}"')
        print(status, data)
        assert status == RESULT_OK, 'expected unsubscribe to return OK'
        assert MAILBOX_UNSUBSCRIBED in data[0], 'expected mailbox unsubscribed message'

    def delete_mailbox(self, name):
        """
        Delete the given mailbox.
        """
        print(f'deleting mailbox: {name}')
        status, data = self.connection.delete(f'"{name}"')
        print(status, data)
        assert status == RESULT_OK, 'expected delete to return OK'
        assert MAILBOX_DELETED in data[0], 'expected mailbox deleted message'

    def do_mailboxes_exist(self, names_to_check):
        """
        Check if the given mailbox(es) exists. Receives list of mailbox names to check for.
        """
        existing_mailboxes = self.get_mailboxes()
        for mailbox in existing_mailboxes:
            if mailbox['name'] in names_to_check:
                print(f'found mailbox: {mailbox['name']}')
                names_to_check.remove(mailbox['name'])
        return True if len(names_to_check) == 0 else False

    def are_mailboxes_subscribed(self, names_to_check):
        """
        Check if the given mailbox(es) are subscribed to. Receives list of mailbox names to check.
        """
        subscribed_mailboxes = self.get_mailboxes(subscribed_only=True)

        for mailbox in subscribed_mailboxes:
            if mailbox['name'] in names_to_check:
                names_to_check.remove(mailbox['name'])

        return True if len(names_to_check) == 0 else False

    def rename_mailbox(self, old_name, new_name):
        """
        Rename an exisating mailbox.
        """
        print(f'renaming mailbox: {old_name} to: {new_name}')
        status, data = self.connection.rename(f'"{old_name}"', f'"{new_name}"') # need double quotes b/c spaces in name
        print(status, data)
        assert status == RESULT_OK, 'expected rename to return OK'
        assert MAILBOX_RENAMED in data[0], 'expected mailbox renamed message'

    def select_mailbox(self, name):
        """
        Select the given mailbox (if none given it will select INBOX by default).
        """
        if name is not None and len(name) > 0:
            print(f'selecting mailbox: {name}')
            status, data = self.connection.select(f'"{name}"')
        else:
            print('selecting mailbox (providing no name so default is selected)')
            status, data = self.connection.select()

        print(status, data)
        assert status == RESULT_OK, 'expected select to return OK'
        assert int(data[0].decode()) >= 0, 'expected number of messages in the selected mailbox to be returned'

    def unselect_mailbox(self):
        """
        If in select state, unselect mailbox; no name required (if any mailbox is selected it will be unselected).
        """
        if self.connection.state != STATE_SELECTED:
            print('no mailbox is currently selected')
            return

        print('unselecting mailbox')
        status, data = self.connection.unselect()
        print(status, data)
        assert status == RESULT_OK, 'expected select to return OK'

        print(f'verifying connection state is: {STATE_AUTH}')
        assert self.connection.state == STATE_AUTH

    def close_mailbox(self):
        """
        If in select state, close mailbox; no name required (if any mailbox is selected it will be closed).
        """
        if self.connection.state != STATE_SELECTED:
            return

        print('\nclosing selected mailbox')
        status, data = self.connection.close()
        print(status, data)

        assert status == RESULT_OK, 'expected close to return OK'
        assert MAILBOX_CLOSE_COMPLETED in data[0], 'expected close completed message'

    def cleanup_test_mailboxes(self):
        """
        Find all existing mailboxes that were previously created by these tests and delete them.
        Mailboxes might have children i.e. subfolders, and we must delete the mailboxes in order
        from lowest to highest levels; the solution is to sort the list of mailboxes to delete
        based on the name and delete the longest names (lowest level subfolders) first.
        """
        existing_mailboxes = self.get_mailboxes()
        sorted_mailboxes = sorted(existing_mailboxes, key=lambda x: x['name'], reverse=True)

        for mailbox in sorted_mailboxes:
            if MAILBOX_PREFIX in mailbox['name']:
                print(f'deleting mailbox: {mailbox['name']}')
                try:
                    self.delete_mailbox(mailbox['name'])
                except:
                    # we don't really care if it failed for some reason as just cleaning up
                    pass
