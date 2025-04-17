import time

from email.message import EmailMessage
from email import message_from_bytes
from imaplib import IMAP4_SSL

from const import (
    TEST_SERVER_HOST,
    IMAP_PORT,
    CONNECT_TIMEOUT,
    RESULT_OK,
    STATE_NONAUTH,
    STATE_LOGOUT,
    MAILBOX_SUBSCRIBED,
    MAILBOX_CREATED,
    MAILBOX_DELETED,
    MAILBOX_UNSUBSCRIBED,
    LOGOUT_BYE,
    MAILBOX_PREFIX,
    MAILBOX_RENAMED,
    STATE_SELECTED,
    STATE_AUTH,
    MAILBOX_CLOSE_COMPLETED,
    TEST_MSG_SUBJECT_PREFIX,
    TEST_MSG_DEL_SUBJECT_PREFIX,
    TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX,
    TEST_MSG_BODY_PREFIX,
    TEST_ACCT_1_EMAIL,
    TEST_ACCT_2_EMAIL,
    APPEND_COMPLETED,
    MSG_DELETED_FLAG,
    MSG_SEEN_FLAG,
    MSG_COPIED,
)

from utils import convert_raw_mailbox_list


class IMAP:
    def __init__(self):
        self.connection = None

    def login(self, username, password):
        """
        Connect and log into the imap server as defined in the .env.test file.
        """
        success = False
        print(f'\nconnecting to imap host: {TEST_SERVER_HOST}')

        try:
            self.connection = IMAP4_SSL(TEST_SERVER_HOST, IMAP_PORT, timeout=CONNECT_TIMEOUT)
            if self.connection.state == STATE_NONAUTH:
                print('connected, now signing in to imap')
                self.connection.login(username, password)
                if self.connection.state == STATE_AUTH:
                    success = True
                    print(f'successfully signed into imap host: {TEST_SERVER_HOST}')

        except Exception as e:
            print(str(e))

        return success

    def logout(self):
        """
        Log out of the IMAP server.
        """
        if self.connection is not None and self.connection.state != STATE_LOGOUT:
            print(f'\nlogging out of imap host: {TEST_SERVER_HOST}')

            try:
                resp = IMAP4_SSL.logout(self.connection)
            except Exception as e:
                print(str(e))

            if LOGOUT_BYE in resp and self.connection.state == STATE_LOGOUT:
                print(f'successfullly signed out of imap host: {TEST_SERVER_HOST}')
                return True
        else:
            print('logout called however you are not currenty logged in to imap')
        return False

    def get_capabilities(self):
        """
        Retrieve the list of IMAP server capabilities.
        """
        status = None
        capabilities = None

        if self.connection is not None and self.connection.state == STATE_AUTH:
            print('requesting imap server capabilities')
            status, raw_capabilities = IMAP4_SSL.capability(self.connection)
            capabilities = raw_capabilities[0].decode().split()
        else:
            print('unable to retrieve capabilities (not logged in to imap server)')
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
        status, data = self.connection.create(f'"{name}"')  # need double quotes b/c spaces in name
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
                print(f'found mailbox: {mailbox["name"]}')
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
        Rename an existing mailbox.
        """
        print(f'renaming mailbox: {old_name} to: {new_name}')
        status, data = self.connection.rename(f'"{old_name}"', f'"{new_name}"')  # need double quotes b/c spaces in name
        print(status, data)
        assert status == RESULT_OK, 'expected rename to return OK'
        assert MAILBOX_RENAMED in data[0], 'expected mailbox renamed message'

    def select_mailbox(self, name=None):
        """
        Select the given mailbox (if none given it will select INBOX by default).
        """
        if name is not None and len(name) > 0:
            print(f'selecting mailbox: {name}')
            status, data = self.connection.select(f'"{name}"')
        else:
            print('selecting default mailbox (inbox)')
            status, data = self.connection.select()

        print(status, data)
        assert status == RESULT_OK, 'expected select to return OK'
        msg_count = int(data[0].decode())
        assert msg_count >= 0, 'expected number of messages in the selected mailbox to be returned'

        return msg_count

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
                print(f'deleting mailbox: {mailbox["name"]}')
                try:
                    self.delete_mailbox(mailbox['name'])
                except Exception as _ex:
                    # we don't really care if it failed for some reason as just cleaning up
                    pass

    def cleanup_test_messages(self):
        """
        Find all existing email messages that were previously created by these tests and delete them.
        """
        self.select_mailbox() # select inbox
        prev_test_msgs = self.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        more_prev_test_msgs = self.search_messages('SUBJECT', TEST_MSG_DEL_SUBJECT_PREFIX)
        even_more_prev_test_msgs = self.search_messages('SUBJECT', TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX)
        prev_test_msgs.extend(more_prev_test_msgs)
        prev_test_msgs.extend(even_more_prev_test_msgs)

        for msg_id in prev_test_msgs:
            print(f'deleting old test email {msg_id}')
            try:
                self.connection.store(msg_id, "+FLAGS", "\\Deleted")
                time.sleep(1)
            except Exception as _ex:
                # we don't really care if it failed for some reason as just cleaning up
                pass

        # now permanently delete the deleted emails
        if prev_test_msgs:
            try:
                print('expunging deleted messages')
                self.permanently_delete_msgs()
            except Exception as _ex:
                # we don't really care if it failed for some reason as just cleaning up
                pass

    def cleanup_draft_test_messages(self):
        """
        Find all existing draft email messages that were previously created by these tests and delete them.
        """
        self.select_mailbox('Drafts')
        prev_draft_test_msgs = self.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)

        for msg_id in prev_draft_test_msgs:
            print(f'deleting old test email {msg_id}')
            try:
                self.connection.store(msg_id, "+FLAGS", "\\Deleted")
                time.sleep(1)
            except Exception as _ex:
                # we don't really care if it failed for some reason as just cleaning up
                pass

        # now permanently delete the deleted emails
        if prev_draft_test_msgs:
            try:
                print('expunging deleted messages')
                self.connection.expunge()

            except Exception as _ex:
                # we don't really care if it failed for some reason as just cleaning up
                pass

    def search_messages(self, criteria1, criteria2=None):
        """
        Search the currently selected mailbox for messages using the given criteria; and return
        a list of IDs of messagest that were found (that matched the criteria).
        """
        print(f'searching for messages using criteria: {criteria1} {criteria2 if criteria2 != None else ''}')
        charSet = None # will defaul to UTF-8

        result, found_msg_ids = self.connection.search(
            charSet,
            criteria1, # i.e. 'ALL'
            f'"{criteria2}"' if criteria2 != None else None # double quotes as if included search string might have space
        )
        print(result, found_msg_ids)

        # search returns a status and list of message ids for the found messages i.e:
        # OK, [b'1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25']
        assert result == RESULT_OK, 'expected search to return OK'
        found_msg_ids_list = found_msg_ids[0].decode().split()
        print(f'found {len(found_msg_ids_list)} messages')

        return found_msg_ids_list

    def create_draft_email(self, subject="Test email"):
        # create a draft email to test_acct_1 (from test_acct_2)
        print(f'creating draft email from test_acct_2 to test_acct_1 with the subject: {subject}')

        self.select_mailbox('Drafts')

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = TEST_ACCT_1_EMAIL
        msg['To'] = TEST_ACCT_2_EMAIL
        msg.set_content(TEST_MSG_BODY_PREFIX)

        result, data = self.connection.append('Drafts', '\\Draft', None, str(msg).encode('utf-8'))
        print(result, data)

        assert result == RESULT_OK
        assert APPEND_COMPLETED in data[0]

        return True

    def delete_messages(self, msg_ids):
        """
        Mark the given message(s) as deleted (in the currently selected mailbox).
        """
        for msg in msg_ids:
            print(f'marking message {msg} as deleted')
            result, data = self.connection.store(msg, "+FLAGS", "\\Deleted")
            print(result, data)
            assert result == RESULT_OK, 'expected to be able to mark message as deleted'
            assert MSG_DELETED_FLAG in data[0], 'expected deleted flag to have been added'

    def permanently_delete_msgs(self):
        """
        Permanently delete all messages that are marked as deleted in the currently selected mailbox.
        """
        print(f'expunging all deleted messages in current mailbox')
        result, data = self.connection.expunge()
        print(result, data)
        assert result == RESULT_OK, 'expected expunge to return OK'

    def mark_message_read(self, msg_id, confirm=True):
        """
        Mark the given message as read (in the currently selected mailbox). If the given message is already
        marked read then the store command won't return the \\Seen flag in the command result data; so give
        an option to confirm or not, as some cases we may call this not knowing if the msg is read already.
        """
        print(f'marking message {msg_id} as read')
        result, data = self.connection.store(msg_id, "+FLAGS", "\\Seen")
        print(result)
        assert result == RESULT_OK, 'expected to be able to mark message as read'
        if confirm:
            assert MSG_SEEN_FLAG in data[0], 'expected seen flag to have been added'

    def mark_message_unread(self, msg_id):
        """
        Mark the given message as unread (in the currently selected mailbox). This means removing
        the '\\Seen' flag if it exists (as there is no UNSEEN flag).
        """
        print(f'marking message {msg_id} as unread')
        result, data = self.connection.store(msg_id, "-FLAGS", "\\Seen")
        print(result)
        assert result == RESULT_OK, 'expected to be able to mark message as unread'

    def fetch_message_details(self, msg_id):
        """
        Fetch the given message (by id) from the currently selected mailbox and return it
        in a nicely formatted message structure.
        """
        print(f'fetching message {msg_id}')
        result, data = self.connection.fetch(msg_id, '(RFC822)') # get message details
        print(result)
        assert result == RESULT_OK, 'expected fetch message to return OK'
        assert len(data) == 2, 'expected message data to be returned'

        # use python's email message module to parse raw message data into useful object
        parsed_msg = message_from_bytes(data[0][1])
        print(f'fetched message details, message subject is: {parsed_msg['Subject']}')

        return parsed_msg

    def fetch_message_flags(self, msg_id):
        """
        Fetch the flags for the given message id (from the currently selected mailbox).
        """
        print(f'fetching message {msg_id} flags')
        result, msg_flags = self.connection.fetch(msg_id, '(FLAGS)') # get flags only
        print(result, msg_flags)
        assert result == RESULT_OK, 'expected fetch message flags to return OK'
        assert msg_flags, 'expected message flags to be returned'

        return msg_flags

    def fetch_message_internal_date(self, msg_id):
        """
        Fetch the internal date for the given message id (from the currently selected mailbox).
        """
        print(f'fetching message {msg_id} internal date')
        result, date = self.connection.fetch(msg_id, '(INTERNALDATE)') # get flags only
        print(result, date)
        assert result == RESULT_OK, 'expected fetch message internal date to return OK'
        assert len(date[0]) != 0, 'expected message internal date to be returned'

        return date

    def copy_message(self, msg_id, destination_mailbox):
        """
        Copy the given message into the given destination mailbox/folder.
        """
        print(f'copying message {msg_id} into folder: {destination_mailbox}')
        result, data = self.connection.copy(msg_id, f'"{destination_mailbox}"')
        print(result, data)
        assert result == RESULT_OK, 'expected copy message to return OK'
        assert MSG_COPIED in data[0], 'expected message copied message'

    def append_message_to_inbox(self, subject='Test message'):
        # use append to write a message directly to the inbox
        print(f'creating and appending messge to test_acct_1 inbox with the subject: {subject}')

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = TEST_ACCT_1_EMAIL
        msg['To'] = TEST_ACCT_2_EMAIL
        msg.set_content(TEST_MSG_BODY_PREFIX)

        result, data = self.connection.append('INBOX', None, None, str(msg).encode('utf-8'))
        print(result, data)

        assert result == RESULT_OK
        assert APPEND_COMPLETED in data[0]

        return True
