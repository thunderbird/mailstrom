import datetime, os, pytest, time, uuid

from IMAP import IMAP

from common.logger import log

from const import (
    IMAP_MSG_TESTS_EMAIL_COUNT,
    IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT,
    RESULT_OK,
    RESULT_NO,
    TEST_ACCT_1_EMAIL,
    TEST_ACCT_2_EMAIL,
    TEST_MSG_SUBJECT_PREFIX,
    TEST_MSG_DEL_SUBJECT_PREFIX,
    TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX,
    TEST_MSG_BODY_PREFIX,
    TEST_MSG_MIME_VER,
    MSG_SEEN_FLAG,
    MAILBOX_PREFIX,
    MSG_COPY_SAME_LOCATION,
    CONTENT_TYPE_TEXT_PLAIN,
    CONTENT_TYPE_MULTI_MIXED,
    CONTENT_TYPE_PNG,
    TRANS_ENCODING_7BIT,
    TRANS_ENCODING_BASE64,
    CONTENT_DISP_ATTACHMENT,
    DOWNLOAD_EMAIL_ATTACHMENTS_PATH,
    TEST_MSG_ATTACHMENT,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


@pytest.mark.usefixtures("populate_inbox")
class TestIMAPMessaging():
    """
    IMAP messaging tests.
    These tests require specific emails to already exist in the test_acct_1 inbox. These emails
    are automatically created and sent to our test_acct_1 email by the populate_inbox pytest fixture
    which runs one time before any of these tests start. So before the tests start the test_acct_1
    inbox will contain at least IMAP_MSG_TESTS_EMAIL_COUNT messages. These tests are specifically
    for IMAP messaging even though they use SMTP to populate the inbox first; there will be separate
    tests specifically for SMTP.
    """
    def test_search_all_messages(self, imap):
        # select inbox and search for all messages
        imap.select_mailbox()
        found_msgs = imap.search_messages('ALL')
        assert len(found_msgs) >= IMAP_MSG_TESTS_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_EMAIL_COUNT} messages to have been found'

    def test_search_messages_matching_to(self, imap):
        # search inbox for messages with specific email in to: field
        imap.select_mailbox()
        found_msgs = imap.search_messages('TO', TEST_ACCT_1_EMAIL)
        assert len(found_msgs) >= IMAP_MSG_TESTS_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_EMAIL_COUNT} messages to have been found'

        # now search using an email we know doesn't exist, so should return 0 messages
        found_msgs = imap.search_messages('TO', 'nope@nope.com')
        assert len(found_msgs) == 0, 'expected search to return 0 messages'

    def test_search_messages_matching_from(self, imap):
        # search inbox for messages with specific email in from: field
        imap.select_mailbox()
        found_msgs = imap.search_messages('FROM', TEST_ACCT_2_EMAIL)
        assert len(found_msgs) >= IMAP_MSG_TESTS_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_EMAIL_COUNT} messages to have been found'

        # now search using an email we know doesn't exist, so should return 0 messages
        found_msgs = imap.search_messages('FROM', 'nope@nope.com')
        assert len(found_msgs) == 0, 'expected search to return 0 messages'

    def test_search_messages_matching_subject(self, imap):
        # search inbox for messages that contain specified text in message subject
        imap.select_mailbox()
        found_msgs = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        assert len(found_msgs) >= IMAP_MSG_TESTS_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_EMAIL_COUNT} messages to have been found'

        # now search using a subject we know doesn't exist, so should return 0 messages
        found_msgs = imap.search_messages('SUBJECT', 'The quick brown fox jumps over the lazy dog')
        assert len(found_msgs) == 0, 'expected search to return 0 messages'

    def test_search_messages_matching_body(self, imap):
        # search inbox for messages that contain specified text in message body
        imap.select_mailbox()
        found_msgs = imap.search_messages('BODY', TEST_MSG_BODY_PREFIX)
        assert len(found_msgs) >= IMAP_MSG_TESTS_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_EMAIL_COUNT} messages to have been found'

        # now search using a text we know won't exist in any message body, so should return 0 messages
        found_msgs = imap.search_messages('BODY', f'nope{uuid.uuid4()}')
        assert len(found_msgs) == 0, 'expected search to return 0 messages'

    def test_search_messages_draft(self, smtp, imap):
        # search for draft messages
        imap.select_mailbox('Drafts')
        found_msgs = imap.search_messages('DRAFT')
        assert len(found_msgs) >= IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT} draft messages to have been found'

    def test_search_messages_deleted(self, imap):
        # delete one of our test messages that already exists in the inbox and is allocated
        # for a deletion test (must use test message specifially allocated for a delete test
        # so that other tests are not impacted)
        imap.select_mailbox()
        msgs_ids = imap.search_messages('SUBJECT', TEST_MSG_DEL_SUBJECT_PREFIX)
        assert len(msgs_ids) > 0, 'expected test messages to already exist in test_acct_1 inbox'
        imap.delete_messages([msgs_ids[0]])

        # now we know we have at least 1 deleted message, search for deleted
        found_msgs = imap.search_messages('DELETED')
        assert len(found_msgs) >= 1, f'expected at least 1 deleted messages to have been found'

        # now permanently remove deleted messages and search again, should now be 0
        imap.permanently_delete_msgs()
        time.sleep(1)
        found_msgs = imap.search_messages('DELETED')
        assert len(found_msgs) == 0, 'expected 0 deleted messages to have been found'

    def test_search_messages_unread(self, imap):
        # mark one of our inbox test messages as unread, then search for unread messages 
        imap.select_mailbox()
        msgs = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        assert len(msgs) > 0, 'expected test messages to already exist in test_acct_1 inbox'
        imap.mark_message_unread(msgs[2])
        time.sleep(1)
        found_msgs = imap.search_messages('UNSEEN')
        assert len(found_msgs) >= 1, f'expected at least 1 unread message to have been found'

    def test_search_messages_read(self, imap):
        # mark one of our inbox test messages as read, then search for read messages
        imap.select_mailbox()
        msgs = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        assert len(msgs) > 0, 'expected test messages to already exist in test_acct_1 inbox'
        imap.mark_message_read(msgs[0])
        time.sleep(1)
        found_msgs = imap.search_messages('SEEN')
        assert len(found_msgs) >= 1, f'expected at least 1 read message to have been found'

    def test_search_messages_rcvd_on_date(self, imap):
        # search inbox for messages received today; test setup ensured we already received messages today
        imap.select_mailbox()
        today = datetime.datetime.now().strftime("%d-%b-%Y") # IMAP requires dd-mm-yyyy ie. 23-Apr-2025
        found_msgs = imap.search_messages(f'ON {today}')
        assert len(found_msgs) >= IMAP_MSG_TESTS_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_EMAIL_COUNT} messages to have been found'

        # search inbox for messages received on a date that we know we never received any msgs on
        found_msgs = imap.search_messages(f'ON 01-Jan-2025')
        assert len(found_msgs) == 0, f'expected to find 0 messages'

    def test_mark_message_read(self, imap):
        # we need an unread message to start; select one of our existing inbox test messages
        imap.select_mailbox()
        unread_msgs = imap.search_messages('UNSEEN SUBJECT', TEST_MSG_SUBJECT_PREFIX)

        # if we don't have any unread test messages mark one unread and verify
        if len(unread_msgs) == 0:
            log.debug('no unread test messages found, so marking one unread first')
            msgs = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)
            assert len(msgs) > 0, 'expected test messages to already exist in test_acct_1 inbox'
            test_msg = msgs[0]
            imap.mark_message_unread(test_msg)
            time.sleep(1)
            unread_msgs = imap.search_messages('UNSEEN SUBJECT', TEST_MSG_SUBJECT_PREFIX)
            assert len(unread_msgs) > 0, 'expected message to have been marked unread'
        else:
            test_msg = unread_msgs[0]

        # now mark our test message as read
        imap.mark_message_read(test_msg)

        # get the test message flags and verify it is now marked read
        msg_flags = imap.fetch_message_flags(test_msg)
        assert MSG_SEEN_FLAG in msg_flags[0]

    def test_mark_message_unread(self, imap):
        # we need a read message to start; select one of our existing inbox test messages
        imap.select_mailbox()
        read_msgs = imap.search_messages('SEEN SUBJECT', TEST_MSG_SUBJECT_PREFIX)

        # if we don't have any read test messages mark one read and verify
        if len(read_msgs) == 0:
            log.debug('no read test messages found, so marking one read first')
            msgs = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)
            assert len(msgs) > 0, 'expected test messages to already exist in test_acct_1 inbox'
            test_msg = msgs[0]
            imap.mark_message_read(test_msg)
            time.sleep(1)
            read_msgs = imap.search_messages('SEEN SUBJECT', TEST_MSG_SUBJECT_PREFIX)
            assert len(read_msgs) > 0, 'expected message to have been marked read'
        else:
            test_msg = read_msgs[0]

        # now mark our test message as unread
        imap.mark_message_unread(test_msg)

        # get the test message flags and verify it is now marked unread (which just means
        # there's NOT a SEEN flag)
        msg_flags = imap.fetch_message_flags(test_msg)
        assert MSG_SEEN_FLAG not in msg_flags[0]

    def test_copy_message(self, imap):
        # select one of existing test messges that currently resides in the inbox
        start_inbox_msg_count = imap.select_mailbox()
        msg_id = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)[0]

        # fetch subject of our selected message
        msg_subject = imap.fetch_message_details(msg_id)['Subject']
        log.debug(f'message to be copied has this subject: {msg_subject}')

        # create and subscribe to a new test folder
        destination = f'{MAILBOX_PREFIX} Move Msg Test {datetime.datetime.now()}'
        imap.create_mailbox(destination)
        imap.subscribe_mailbox(destination)

        # select new folder, should have zero messages
        msg_count = imap.select_mailbox(destination)
        assert msg_count == 0, 'expected no messgaes to exist in newly created folder'

        # now copy our test message from the inbox into the new test folder
        imap.select_mailbox()
        imap.copy_message(msg_id, destination)

        # now switch to the new test folder and search for our message, should find it
        msg_count = imap.select_mailbox(destination)
        assert msg_count == 1, 'expected message to be moved into destination folder'

        found_msg = imap.search_messages('SUBJECT', msg_subject)
        assert len(found_msg) == 1, 'expected to find the copied message in the new folder'

        # now switch back to inbox and search again, message should still be found there too
        after_inbox_msg_count = imap.select_mailbox()
        assert after_inbox_msg_count == start_inbox_msg_count, 'expected inbox message count to be the same as before the copy'

        found_msg = imap.search_messages('SUBJECT', msg_subject)
        assert len(found_msg) == 1, 'expected to find the original copied message in the inbox'

    def test_copy_message_same_folder(self, imap):
        # attempt to copy message into same mailbox, expect err
        imap.select_mailbox()
        msg_id = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)[0]

        msg_subject = imap.fetch_message_details(msg_id)['Subject']
        log.debug(f'message to be copied has this subject: {msg_subject}')

        log.debug(f'attempting to copy message {msg_id} from INBOX into INBOX, expect error')
        result, data = imap.connection.copy(msg_id, 'INBOX')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected copy to return NO'
        assert MSG_COPY_SAME_LOCATION in data[0], 'expected same source and destination message'

    def test_delete_message(self, imap):
        # delete one of our test messages that already exists in the inbox and is allocated
        # for a deletion test (must use test message specifically allocated for a delete test
        # so that other tests are not impacted)
        imap.select_mailbox()
        msgs_ids = imap.search_messages('SUBJECT', TEST_MSG_DEL_SUBJECT_PREFIX)
        assert len(msgs_ids) > 0, 'expected test messages to already exist in test_acct_1 inbox'
        test_msg = msgs_ids[0]

        msg_subject = imap.fetch_message_details(test_msg)['Subject']
        log.debug(f'message to be deleted has this subject: {msg_subject}')

        imap.delete_messages(test_msg)

        # search for deleted message and verify still there; flag was already checked in delete_messages above
        found_msg = imap.search_messages('SUBJECT', msg_subject)
        assert len(found_msg) == 1, 'expected to find the deleted message'

    def test_expunge_message(self, imap):
        # delete message, expunge, verify message was permanently removed
        imap.select_mailbox()
        msgs_ids = imap.search_messages('SUBJECT', TEST_MSG_DEL_SUBJECT_PREFIX)
        assert len(msgs_ids) > 0, 'expected test messages to already exist in test_acct_1 inbox'
        test_msg = msgs_ids[1]

        msg_subject = imap.fetch_message_details(test_msg)['Subject']
        log.debug(f'message to be deleted has this subject: {msg_subject}')

        imap.delete_messages(test_msg)

        # search for deleted message and verify still there; flag was already checked in delete_messages above
        found_msg = imap.search_messages('SUBJECT', msg_subject)
        assert len(found_msg) == 1, 'expected to find the deleted message'

        # now expunge then verify message no longer exists / was permanently deleted
        imap.permanently_delete_msgs()
        found_msg = imap.search_messages('SUBJECT', msg_subject)
        assert len(found_msg) == 0, 'expected NOT to find the deleted message after calling expunge'

    def test_fetch_message_details(self, imap):
        # fetch message details from a test message in the test_acct_1 inbox
        imap.select_mailbox()
        msg_ids = imap.search_messages('SUBJECT', {TEST_MSG_SUBJECT_PREFIX})

        # fetch the first message and verify contents
        msg = imap.fetch_message_details(msg_ids[0])
        assert msg, 'expected message to have been fetched'

        assert msg['Delivered-To'] == TEST_ACCT_1_EMAIL, 'expected message delivered-to field to be test_acct_1 email'
        assert msg['To'] == TEST_ACCT_1_EMAIL, 'expected message to field to be test_acct_1 email'
        assert msg['From'] == TEST_ACCT_2_EMAIL, 'expected message from field to be test_acct_2 email'
        assert TEST_MSG_SUBJECT_PREFIX in msg['Subject'], 'expected message subject to be correct'
        assert TEST_MSG_MIME_VER in msg['MIME-Version'], 'expected message MIME version to be correct'
        assert msg['Content-Transfer-Encoding'] == TRANS_ENCODING_7BIT, 'expected message transfer encoding to be correct'
        assert msg['Content-Type'] == CONTENT_TYPE_TEXT_PLAIN, 'expected message content-type to be correct'

    def test_fetch_message_flags(self, imap):
        # fetch the flags from a test message in the test_acct_1 inbox
        imap.select_mailbox()
        test_msg_id = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)[1]

        # mark one of our inbox test messages as read first, so their is a flag
        imap.mark_message_read(test_msg_id, confirm=False)
        time.sleep(1)

        # fetch the message flags and verify
        flags = imap.fetch_message_flags(test_msg_id)
        assert len(flags) != 0, 'expected message flags to be returned'
        assert MSG_SEEN_FLAG in flags[0], 'expected message seen flag to have been returned'

    def test_fetch_message_date(self, imap):
        # fetch the internal date from a test_acct_1 inbox test message that was received today
        imap.select_mailbox()
        msg_id = imap.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)[0]

        # fetch the message internaldate and verify, will be in this format: "24-Apr-2025 18:15:40 +0000"
        internal_date = imap.fetch_message_internal_date(msg_id)[0]
        today = datetime.datetime.now().strftime("%d-%b-%Y")
        assert today in internal_date.decode(), 'expected internal date to be correct'

    def test_fetch_message_attachment(self, imap):
        # fetch an email that has an attachment and retrieve the attachment; our populate_inbox fixture
        # has already sent an email with an attachment to test_acct_1 inbox
        imap.select_mailbox()
        msg_id = imap.search_messages('SUBJECT', TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX)[0]

        # fetch message details to verify there is an attachment
        msg = imap.fetch_message_details(msg_id)
        assert msg, 'expected message to have been fetched'
        assert msg.is_multipart(), 'expectected message to be multi-part'
        assert CONTENT_TYPE_MULTI_MIXED in msg['Content-Type'], 'expected message content-type to be correct'

        # now walk through and verify each part of the message
        msg_part = 0
        for part in msg.walk():
            msg_part += 1
            if msg_part == 1:
                # message top-level
                assert CONTENT_TYPE_MULTI_MIXED in part['Content-Type'], 'expected msg part 1 content-type to be correct'
                assert msg['Delivered-To'] == TEST_ACCT_1_EMAIL, 'expected message delivered-to field to be test_acct_1 email'
                assert msg['To'] == TEST_ACCT_1_EMAIL, 'expected message to field to be test_acct_1 email'
                assert msg['From'] == TEST_ACCT_2_EMAIL, 'expected message from field to be test_acct_2 email'
                assert TEST_MSG_WITH_ATTACHMENT_SUBJECT_PREFIX in msg['Subject'], 'expected message subject to be correct'
                assert part['MIME-Version'] == TEST_MSG_MIME_VER, 'expected message MIME version to be correct'

            elif msg_part == 2:
                # text part of message
                assert part['Content-Type'] == CONTENT_TYPE_TEXT_PLAIN, 'expected msg part 2 content type to be correct'
                assert part['Content-Transfer-Encoding'] == TRANS_ENCODING_7BIT, 'expected msg part 2 transfer encoding to be correct'
                assert TEST_MSG_BODY_PREFIX in part.get_payload(), 'expected message body text to be in the msg part 2'

            elif msg_part == 3:
                # attachment
                assert part['Content-Type'] == CONTENT_TYPE_PNG, 'expected msg part 2 content type to be correct'
                assert part['Content-Transfer-Encoding'] == TRANS_ENCODING_BASE64, 'expected msg part 2 transfer encoding to be correct'
                assert part['MIME-Version'] == TEST_MSG_MIME_VER, 'expected msg part 2 MIME version to be correct'
                assert part['Content-Disposition'] == CONTENT_DISP_ATTACHMENT, 'expected msg part 2 content disposition to be correct'

                # actually download the attachment
                download_to = DOWNLOAD_EMAIL_ATTACHMENTS_PATH + 'imap-msg-test-download.png'
                log.debug(f'downloading email msg attachment to: {download_to} ')
                try:
                    with open(download_to, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                except Exception as e:
                    log.debug(str(e))

                assert os.path.isfile(download_to), 'expected downloaded file to exist'

                # compare the dowloaded file with the file that was attached when the email was originally sent by the populate_inbox fixture
                og_stats = os.stat(TEST_MSG_ATTACHMENT)
                df_stats = os.stat(download_to)
                assert df_stats.st_size == og_stats.st_size, 'expected downloaded attachment size to match original file size'
                assert df_stats.st_ctime > og_stats.st_ctime, 'expected downlaoded attachment ctime to be > original file ctime'

        assert msg_part == 3, 'expected message to have 3 parts'

    def test_fetch_message_marks_read(self, imap):
        # after an unread message is fetched from the inbox, it should automatically be marked as read
        log.debug('selecting an unread message')
        imap.select_mailbox()
        unread_msgs = imap.search_messages('UNSEEN SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        assert len(unread_msgs) >= 1, 'expected at least one unread message in the inbox'
        test_msg_id = unread_msgs[0]

        # first time fetchimg the mesage it should be marked as unread
        test_msg_flags = imap.fetch_message_flags(test_msg_id)
        assert MSG_SEEN_FLAG not in test_msg_flags[0], 'expected message to be marked unread'

        # now fetch the message details
        msg_details = imap.fetch_message_details(test_msg_id)

        # now check the flags for the same message and this time it should be marked read
        test_msg_flags = imap.fetch_message_flags(test_msg_id)
        assert MSG_SEEN_FLAG in test_msg_flags[0], 'expected message to now be marked read after fetching'

    def test_append_message_to_inbox(self, imap):
        # put a new message directly in the inbox using append and verify
        msg_subject = f'{TEST_MSG_SUBJECT_PREFIX} Appended {datetime.datetime.now()}'
        imap.append_message_to_inbox(msg_subject)
        imap.select_mailbox()
        found_id = imap.search_messages('SUBJECT', msg_subject)
        assert len(found_id) == 1, 'expected to find the appended message in the test_acct_1 inbox'

    def test_multi_connection_search(self, imap):
        # able to open multiple imap connections and select a mailbox and search using each connection
        c1 = imap;

        log.debug('creating 2nd imap connection')
        c2 = IMAP()
        success = c2.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert success, 'expected imap auth to be successful'

        # select inbox for first connection, we know messages exist
        log.debug('selecting and searching inbox using first connection')
        msg_count = c1.select_mailbox()
        assert msg_count != 0, 'expected inbox to have messages'

        found_msgs = c1.search_messages('SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        assert len(found_msgs) > 0, 'expected messages to have been found in the inbox'

        # select drafts for second connection, we know draft messages exist
        log.debug('selecting and searching drafts folder using second connection')
        msg_count = c2.select_mailbox('Drafts')
        assert msg_count != 0, 'expected drafts folder to have messages'

        found_msgs = c2.search_messages('DRAFT')
        assert len(found_msgs) >= IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT, \
            f'expected at least {IMAP_MSG_TESTS_DRAFT_EMAIL_COUNT} draft messages to have been found'

        # done with the second connection
        c2.close_mailbox()
        c2.logout()

    def test_multi_connection_fetch(self, imap):
        # able to open multiple imap connections and fetch a message using each connection
        c1 = imap;

        log.debug('creating 2nd imap connection')
        c2 = IMAP()
        success = c2.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert success, 'expected imap auth to be successful'

        c1.select_mailbox()
        c1_msg_ids = c1.search_messages('SUBJECT', {TEST_MSG_SUBJECT_PREFIX})

        # use the first connection to fetch the first message and verify contents
        log.debug('fetching a message from the inbox using the first connection')
        c1_msg = c1.fetch_message_details(c1_msg_ids[0])
        assert c1_msg, 'expected message to have been fetched using first connection'

        assert c1_msg['Delivered-To'] == TEST_ACCT_1_EMAIL, 'expected message delivered-to field to be test_acct_1 email'
        assert c1_msg['To'] == TEST_ACCT_1_EMAIL, 'expected message to field to be test_acct_1 email'
        assert c1_msg['From'] == TEST_ACCT_2_EMAIL, 'expected message from field to be test_acct_2 email'
        assert TEST_MSG_SUBJECT_PREFIX in c1_msg['Subject'], 'expected message subject to be correct'
        assert TEST_MSG_MIME_VER in c1_msg['MIME-Version'], 'expected message MIME version to be correct'
        assert c1_msg['Content-Transfer-Encoding'] == TRANS_ENCODING_7BIT, 'expected message transfer encoding to be correct'
        assert c1_msg['Content-Type'] == CONTENT_TYPE_TEXT_PLAIN, 'expected message content-type to be correct'

        c2.select_mailbox()
        c2_msg_ids = c2.search_messages('SUBJECT', {TEST_MSG_SUBJECT_PREFIX})

        # use the second connection to fetch the first message and verify contents
        log.debug('fetching a message from the inbox using the second connection')
        c2_msg = c2.fetch_message_details(c2_msg_ids[0])
        assert c2_msg, 'expected message to have been fetched using second connection'

        # messages fetched from both connections should be the same
        for msg_attr in c1_msg:
            assert c1_msg[msg_attr] == c2_msg[msg_attr], f'expected {msg_attr} for each fetched message to match'

        # done with the second connection
        c2.close_mailbox()
        c2.logout()

    def test_multi_connection_sync_read(self, imap):
        # with multiple imap connections open, have one connection mark a message as read;
        # then verify the other connections see the same message marked as read
        c1 = imap;

        log.debug('creating 2nd imap connection')
        c2 = IMAP()
        success = c2.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert success, 'expected imap auth to be successful'

        # select an unread message using first imap connection
        log.debug('searching for an unread message using the first connection')
        c1.select_mailbox()
        c1_unread_msgs = c1.search_messages('UNSEEN SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        assert len(c1_unread_msgs) >= 1, 'expected at least one unread message in the inbox'
        test_msg_id = c1_unread_msgs[0]

        # use the first imap connection and mark the message as read
        log.debug("using the first connection to mark the message as read")
        c1.mark_message_read(test_msg_id)

        # second connection should see the same message as read; and also one less unread message
        log.debug('verifying that the second connection now sees the same message as marked read')
        c2.select_mailbox()
        c2_unread_msgs = c2.search_messages('UNSEEN SUBJECT', TEST_MSG_SUBJECT_PREFIX)
        assert len(c2_unread_msgs) == len(c1_unread_msgs) -1, 'expected at least one unread message in the inbox'

        c2_test_msg_flags = c2.fetch_message_flags(test_msg_id)
        assert MSG_SEEN_FLAG in c2_test_msg_flags[0], 'expected second connection to see the same message as marked read'

        # done with the second connection
        c2.close_mailbox()
        c2.logout()
