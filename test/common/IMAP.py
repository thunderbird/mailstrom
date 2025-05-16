import gevent
import time

from email.message import EmailMessage
from email import message_from_bytes
from imaplib import IMAP4_SSL

from locust import events

from common.utils import convert_raw_mailbox_list
from common.logger import log

from common.const import (
    RESULT_OK,
    STATE_NONAUTH,
    STATE_LOGOUT,
    MAILBOX_SUBSCRIBED,
    MAILBOX_CREATED,
    MAILBOX_DELETED,
    MAILBOX_UNSUBSCRIBED,
    LOGOUT_BYE,
    MAILBOX_RENAMED,
    STATE_SELECTED,
    STATE_AUTH,
    MAILBOX_CLOSE_COMPLETED,
    APPEND_COMPLETED,
    MSG_DELETED_FLAG,
    MSG_SEEN_FLAG,
    MSG_COPIED,
    TEST_MSG_SUBJECT_PREFIX,
    TEST_MSG_BODY_PREFIX,
)


class IMAP:
    def __init__(self, host, port, timeout):
        self.connection = None
        self.host = host
        self.port = port
        self.connection_timeout = timeout

    def login(self, username, password):
        """
        Connect and log into the imap server as defined in the .env.test file.
        """
        success = False
        log.debug(f'connecting to imap host: {self.host}')

        try:
            self.connection = IMAP4_SSL(self.host, self.port, timeout=self.connection_timeout)
            if self.connection.state == STATE_NONAUTH:
                log.debug('connected, now signing in to imap')
                self.connection.login(username, password)
                if self.connection.state == STATE_AUTH:
                    success = True
                    log.debug(f'successfully signed into imap host: {self.host}')

        except Exception as e:
            log.debug(f'{str(e)}')

        return success

    def logout(self):
        """
        Log out of the IMAP server.
        """
        if self.connection is not None and self.connection.state != STATE_LOGOUT:
            log.debug(f'logging out of imap host: {self.host}')

            try:
                resp = IMAP4_SSL.logout(self.connection)
            except Exception as e:
                log.debug(f'{str(e)}')

            if LOGOUT_BYE in resp and self.connection.state == STATE_LOGOUT:
                log.debug(f'successfullly signed out of imap host: {self.host}')
                return True
        else:
            log.debug('logout called however you are not currenty logged in to imap')
        return False

    def get_capabilities(self):
        """
        Retrieve the list of IMAP server capabilities.
        """
        status = None
        capabilities = None

        if self.connection is not None and self.connection.state == STATE_AUTH:
            log.debug('requesting imap server capabilities')
            status, raw_capabilities = IMAP4_SSL.capability(self.connection)
            capabilities = raw_capabilities[0].decode().split()
        else:
            log.debug('unable to retrieve capabilities (not logged in to imap server)')
        return status, capabilities

    def get_mailboxes(self, subscribed_only=False):
        """
        Retrieve the list of mailboxes and return in a useful format.
        """
        if not subscribed_only:
            log.debug('retrieving list of mailboxes')
            status, raw_data = self.connection.list()
        else:
            log.debug('retrieving list of subscribed mailboxes')
            status, raw_data = self.connection.lsub()

        assert status == RESULT_OK, 'expected list to return OK'
        assert raw_data, 'expected list of mailboxes to be returned'

        # if any mailboxes found send back useful list
        if raw_data[0] is None:
            log.debug('no mailboxes found')
            return []

        log.debug(f'found {len(raw_data)} mailboxes')

        return convert_raw_mailbox_list(raw_data)

    def create_mailbox(self, name, locust=False):
        """
        Create a new mailbox with the given name.
        """
        log.debug(f'creating mailbox: {name}')

        if locust:
            # locust uses gevent greenlets to run concurrent users in single process
            start_time = gevent.get_hub().loop.now()

        status, data = self.connection.create(f'"{name}"')  # need double quotes b/c spaces in name
        log.debug(f'{status}, {data}')

        # if running a locust load test we need to let locust know the create mailbox worked
        if locust:
            events.request.fire(
                request_type='imap',
                name='create_mailbox',
                response_time=(gevent.get_hub().loop.now() - start_time) * 1000,  # convert to ms
                response_length=len(data[0]),
                context=None,
                exception=data[0] if status != RESULT_OK else None,
            )
        else:
            assert status == RESULT_OK, 'expected create to return OK'
            assert MAILBOX_CREATED in data[0], 'expected mailbox created message'

    def subscribe_mailbox(self, name, locust=False):
        """
        Subscribe to the given mailbox. Need to do this so the mailbox appears in some clients like Thunderbird.
        """
        log.debug(f'subscribing to mailbox: {name}')
        status, data = self.connection.subscribe(f'"{name}"')
        log.debug(f'{status}, {data}')

        # if running a locust load test we don't want the load test to stop if subscribe failed
        # as we're only subscribing so that we can view the new folders after if we want to
        if not locust:
            assert status == RESULT_OK, 'expected subscribe to return OK'
            assert MAILBOX_SUBSCRIBED in data[0], 'expected mailbox subscribed message'

    def unsubscribe_mailbox(self, name):
        """
        Unsubscribe the given mailbox.
        """
        log.debug(f'unsubscribing to mailbox: {name}')
        status, data = self.connection.unsubscribe(f'"{name}"')
        log.debug(f'{status}, {data}')
        assert status == RESULT_OK, 'expected unsubscribe to return OK'
        assert MAILBOX_UNSUBSCRIBED in data[0], 'expected mailbox unsubscribed message'

    def delete_mailbox(self, name):
        """
        Delete the given mailbox.
        """
        log.debug(f'deleting mailbox: {name}')
        status, data = self.connection.delete(f'"{name}"')
        log.debug(f'{status}, {data}')
        assert status == RESULT_OK, 'expected delete to return OK'
        assert MAILBOX_DELETED in data[0], 'expected mailbox deleted message'

    def do_mailboxes_exist(self, names_to_check):
        """
        Check if the given mailbox(es) exists. Receives list of mailbox names to check for.
        """
        existing_mailboxes = self.get_mailboxes()
        for mailbox in existing_mailboxes:
            if mailbox['name'] in names_to_check:
                log.debug(f'found mailbox: {mailbox["name"]}')
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
        log.debug(f'renaming mailbox: {old_name} to: {new_name}')
        status, data = self.connection.rename(f'"{old_name}"', f'"{new_name}"')  # need double quotes b/c spaces in name
        log.debug(f'{status}, {data}')
        assert status == RESULT_OK, 'expected rename to return OK'
        assert MAILBOX_RENAMED in data[0], 'expected mailbox renamed message'

    def select_mailbox(self, name=None):
        """
        Select the given mailbox (if none given it will select INBOX by default).
        """
        if name is not None and len(name) > 0:
            log.debug(f'selecting mailbox: {name}')
            status, data = self.connection.select(f'"{name}"')
        else:
            log.debug('selecting default mailbox (inbox)')
            status, data = self.connection.select()

        log.debug(f'{status}, {data}')
        assert status == RESULT_OK, 'expected select to return OK'
        msg_count = int(data[0].decode())
        assert msg_count >= 0, 'expected number of messages in the selected mailbox to be returned'

        return msg_count

    def unselect_mailbox(self):
        """
        If in select state, unselect mailbox; no name required (if any mailbox is selected it will be unselected).
        """
        if self.connection.state != STATE_SELECTED:
            log.debug('no mailbox is currently selected')
            return

        log.debug('unselecting mailbox')
        status, data = self.connection.unselect()
        log.debug(f'{status}, {data}')
        assert status == RESULT_OK, 'expected select to return OK'

        log.debug(f'verifying connection state is: {STATE_AUTH}')
        assert self.connection.state == STATE_AUTH

    def close_mailbox(self):
        """
        If in select state, close mailbox; no name required (if any mailbox is selected it will be closed).
        """
        if self.connection.state != STATE_SELECTED:
            return

        log.debug('closing selected mailbox')
        status, data = self.connection.close()
        log.debug(f'{status}, {data}')

        assert status == RESULT_OK, 'expected close to return OK'
        assert MAILBOX_CLOSE_COMPLETED in data[0], 'expected close completed message'

    def cleanup_test_mailboxes(self, mailbox_prefix):
        """
        Find all existing mailboxes with a name that match the given prefix  and delete them.
        Mailboxes might have children i.e. subfolders, and we must delete the mailboxes in order
        from lowest to highest levels; the solution is to sort the list of mailboxes to delete
        based on the name and delete the longest names (lowest level subfolders) first.
        """
        existing_mailboxes = self.get_mailboxes()
        sorted_mailboxes = sorted(existing_mailboxes, key=lambda x: x['name'], reverse=True)

        for mailbox in sorted_mailboxes:
            if mailbox_prefix in mailbox['name']:
                log.debug(f'deleting mailbox: {mailbox["name"]}')
                try:
                    self.delete_mailbox(mailbox['name'])
                except Exception as _ex:
                    # we don't really care if it failed for some reason as just cleaning up
                    pass

    def cleanup_test_messages(self, msg_subject_prefix_list):
        """
        Find all existing email messages that match the given subject prefixes and delete them.
        """
        self.select_mailbox()  # select inbox

        msgs_to_del = []
        for subject_prefix in msg_subject_prefix_list:
            found_test_msgs = self.search_messages('SUBJECT', subject_prefix)
            msgs_to_del.extend(found_test_msgs)

        for msg_id in msgs_to_del:
            log.debug(f'deleting old test email {msg_id}')
            try:
                self.connection.store(msg_id, '+FLAGS', '\\Deleted')
                time.sleep(1)
            except Exception as _ex:
                # we don't really care if it failed for some reason as just cleaning up
                pass

        # now permanently delete the deleted emails
        if msgs_to_del:
            try:
                log.debug('expunging deleted messages')
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
            log.debug(f'deleting old test email {msg_id}')
            try:
                self.connection.store(msg_id, '+FLAGS', '\\Deleted')
                time.sleep(1)
            except Exception as _ex:
                # we don't really care if it failed for some reason as just cleaning up
                pass

        # now permanently delete the deleted emails
        if prev_draft_test_msgs:
            try:
                log.debug('expunging deleted messages')
                self.connection.expunge()

            except Exception as _ex:
                # we don't really care if it failed for some reason as just cleaning up
                pass

    def search_messages(self, criteria1, criteria2=None):
        """
        Search the currently selected mailbox for messages using the given criteria; and return
        a list of IDs of messagest that were found (that matched the criteria).
        """
        log.debug(f'searching for messages using criteria: {criteria1} {criteria2 if criteria2 is not None else ""}')
        result, found_msg_ids = self.connection.search(
            None,  # will default to UTF-8
            criteria1,  # i.e. 'ALL'
            # double quotes as if included search string might have space
            f'"{criteria2}"' if criteria2 is not None else None,
        )
        log.debug(f'{result}, {found_msg_ids}')

        # search returns a status and list of message ids for the found messages i.e:
        # OK, [b'1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25']
        assert result == RESULT_OK, 'expected search to return OK'
        found_msg_ids_list = found_msg_ids[0].decode().split()
        log.debug(f'found {len(found_msg_ids_list)} messages')

        return found_msg_ids_list

    def create_draft_email(self, from_address, to_address, subject='Test email'):
        # create a draft email to test_acct_1 (from test_acct_2)
        log.debug(f'creating draft email from test_acct_2 to test_acct_1 with the subject: {subject}')

        self.select_mailbox('Drafts')

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_address
        msg['To'] = to_address
        msg.set_content(TEST_MSG_BODY_PREFIX)

        result, data = self.connection.append('Drafts', '\\Draft', None, str(msg).encode('utf-8'))
        log.debug(f'{result}, {data}')

        assert result == RESULT_OK
        assert APPEND_COMPLETED in data[0]

        return True

    def delete_messages(self, msg_ids):
        """
        Mark the given message(s) as deleted (in the currently selected mailbox).
        """
        for msg in msg_ids:
            log.debug(f'marking message {msg} as deleted')
            result, data = self.connection.store(msg, '+FLAGS', '\\Deleted')
            log.debug(f'{result}, {data}')
            assert result == RESULT_OK, 'expected to be able to mark message as deleted'
            assert MSG_DELETED_FLAG in data[0], 'expected deleted flag to have been added'

    def permanently_delete_msgs(self):
        """
        Permanently delete all messages that are marked as deleted in the currently selected mailbox.
        """
        log.debug('expunging all deleted messages in current mailbox')
        result, data = self.connection.expunge()
        log.debug(f'{result}, {data}')
        assert result == RESULT_OK, 'expected expunge to return OK'

    def mark_message_read(self, msg_id, confirm=True):
        """
        Mark the given message as read (in the currently selected mailbox). If the given message is already
        marked read then the store command won't return the \\Seen flag in the command result data; so give
        an option to confirm or not, as some cases we may call this not knowing if the msg is read already.
        """
        log.debug(f'marking message {msg_id} as read')
        result, data = self.connection.store(msg_id, '+FLAGS', '\\Seen')
        log.debug(f'{result}')
        assert result == RESULT_OK, 'expected to be able to mark message as read'
        if confirm:
            assert MSG_SEEN_FLAG in data[0], 'expected seen flag to have been added'

    def mark_message_unread(self, msg_id):
        """
        Mark the given message as unread (in the currently selected mailbox). This means removing
        the '\\Seen' flag if it exists (as there is no UNSEEN flag).
        """
        log.debug(f'marking message {msg_id} as unread')
        result, data = self.connection.store(msg_id, '-FLAGS', '\\Seen')
        log.debug(f'{result}')
        assert result == RESULT_OK, 'expected to be able to mark message as unread'

    def fetch_message_details(self, msg_id):
        """
        Fetch the given message (by id) from the currently selected mailbox and return it
        in a nicely formatted message structure.
        """
        log.debug(f'fetching message {msg_id}')
        result, data = self.connection.fetch(msg_id, '(RFC822)')  # get message details
        log.debug(f'{result}')
        assert result == RESULT_OK, 'expected fetch message to return OK'
        assert len(data) == 2, 'expected message data to be returned'

        # use python's email message module to parse raw message data into useful object
        parsed_msg = message_from_bytes(data[0][1])
        log.debug(f'fetched message details, message subject is: {parsed_msg["Subject"]}')

        return parsed_msg

    def fetch_message_flags(self, msg_id):
        """
        Fetch the flags for the given message id (from the currently selected mailbox).
        """
        log.debug(f'fetching message {msg_id} flags')
        result, msg_flags = self.connection.fetch(msg_id, '(FLAGS)')  # get flags only
        log.debug(f'{result}, {msg_flags}')
        assert result == RESULT_OK, 'expected fetch message flags to return OK'
        assert msg_flags, 'expected message flags to be returned'

        return msg_flags

    def fetch_message_internal_date(self, msg_id):
        """
        Fetch the internal date for the given message id (from the currently selected mailbox).
        """
        log.debug(f'fetching message {msg_id} internal date')
        result, date = self.connection.fetch(msg_id, '(INTERNALDATE)')  # get flags only
        log.debug(f'{result}, {date}')
        assert result == RESULT_OK, 'expected fetch message internal date to return OK'
        assert len(date[0]) != 0, 'expected message internal date to be returned'

        return date

    def copy_message(self, msg_id, destination_mailbox):
        """
        Copy the given message into the given destination mailbox/folder.
        """
        log.debug(f'copying message {msg_id} into folder: {destination_mailbox}')
        result, data = self.connection.copy(msg_id, f'"{destination_mailbox}"')
        log.debug(f'{result}, {data}')
        assert result == RESULT_OK, 'expected copy message to return OK'
        assert MSG_COPIED in data[0], 'expected message copied message'

    def append_message_to_inbox(self, from_address, to_address, subject='Test message'):
        # use append to write a message directly to the inbox
        log.debug(f'creating and appending messge to test_acct_1 inbox with the subject: {subject}')

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = from_address
        msg['To'] = to_address
        msg.set_content(TEST_MSG_BODY_PREFIX)

        result, data = self.connection.append('INBOX', None, None, str(msg).encode('utf-8'))
        log.debug(f'{result}, {data}')

        assert result == RESULT_OK
        assert APPEND_COMPLETED in data[0]

        return True
