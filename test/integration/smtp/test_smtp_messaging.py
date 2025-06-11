import datetime
import os

from common.logger import log

from common.const import (
    TEST_MSG_SUBJECT_PREFIX,
    TEST_MSG_BODY_PREFIX,
    TEST_MSG_BODY_PREFIX_HTML,
    TEST_MSG_ATTACHMENT,
    CONTENT_TYPE_PNG,
    CONTENT_TYPE_MULTI_MIXED,
    CONTENT_TYPE_TEXT_PLAIN_ASCII,
    CONTENT_TYPE_TEXT_HTML,
    TRANS_ENCODING_BASE64,
    CONTENT_DISP_ATTACHMENT,
    DOWNLOAD_EMAIL_ATTACHMENTS_PATH,
)

from const import (
    TEST_ACCT_1_EMAIL,
    TEST_ACCT_2_EMAIL,
)


class TestSMTPMessaging:
    """
    SMTP messaging tests.
    All emails are sent to TEST_ACCT_1_EMAIL from TEST_ACCT_2_EMAIL (we use TEST_ACCT_2 creds to sign into SMTP
    for sending; and we use TEST_ACCT_1 creds to sign into IMAP to verify emails were received). This way all
    integration tests are sending email to the same account, which makes it easier for clean-up.
    """

    def test_send_email_plain_text(self, smtp, imap):
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test plain text {datetime.datetime.now()}'
        send_exception = smtp.send_test_email(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            subject=subject,
            body=TEST_MSG_BODY_PREFIX,
            attachment=None,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

    def test_send_email_plain_text_with_attachment(self, smtp, imap):
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test with attachment {datetime.datetime.now()}'
        send_exception = smtp.send_test_email(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            subject=subject,
            body=TEST_MSG_BODY_PREFIX,
            attachment=TEST_MSG_ATTACHMENT,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

        # make sure message has attachment
        msg = imap.fetch_message_details(msg_arrived)
        assert msg, 'expected message to have been fetched'
        assert msg.is_multipart(), 'expectected message to be multi-part'

        # now walk through and verify each part of the message
        msg_part = 0
        for part in msg.walk():
            msg_part += 1
            if msg_part == 1:
                # message top-level
                pass

            elif msg_part == 2:
                # text part of message
                pass

            elif msg_part == 3:
                # attachment which is what we care about here
                assert part['Content-Type'] == CONTENT_TYPE_PNG, 'expected msg part 2 content type to be correct'
                assert part['Content-Transfer-Encoding'] == TRANS_ENCODING_BASE64, (
                    'expected msg part 2 transfer encoding to be correct'
                )
                assert part['Content-Disposition'] == CONTENT_DISP_ATTACHMENT, (
                    'expected msg part 2 content disposition to be correct'
                )

                # actually download the attachment
                download_to = DOWNLOAD_EMAIL_ATTACHMENTS_PATH + 'smtp-msg-test-download.png'
                log.debug(f'downloading email msg attachment to: {download_to} ')
                try:
                    with open(download_to, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                except Exception as e:
                    log.debug(f'{str(e)}')

                assert os.path.isfile(download_to), 'expected downloaded file to exist'

                # compare the dowloaded file with the file that was attached when the email was originally sent
                og_stats = os.stat(TEST_MSG_ATTACHMENT)
                df_stats = os.stat(download_to)
                assert df_stats.st_size == og_stats.st_size, (
                    'expected downloaded attachment size to match original file size'
                )
                assert df_stats.st_ctime > og_stats.st_ctime, (
                    'expected downlaoded attachment ctime to be > original file ctime'
                )

        assert msg_part == 3, 'expected message to have an attachment'

    def test_send_email_from_not_allowed(self, smtp):
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test {datetime.datetime.now()}'
        send_exception = smtp.send_test_email(
            to_email=TEST_ACCT_1_EMAIL,
            from_email='not.allowed.to.send.from.this.address@example.org',
            subject=subject,
            body=TEST_MSG_BODY_PREFIX,
            attachment=None,
        )
        assert send_exception, 'expected send message to fail'
        assert 'SMTPSenderRefused' in send_exception, 'expected correct exception type'

    def test_send_email_invalid_to(self, smtp):
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test {datetime.datetime.now()}'
        send_exception = smtp.send_test_email(
            to_email='not-a-valid-to-email!',
            from_email=TEST_ACCT_2_EMAIL,
            subject=subject,
            body=TEST_MSG_BODY_PREFIX,
            attachment=None,
        )
        assert send_exception, 'expected send message to fail'
        assert 'SMTPRecipientsRefused' in send_exception, 'expected correct exception type'

    def test_send_email_html(self, smtp, imap):
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test html {datetime.datetime.now()}'
        send_exception = smtp.send_test_email_multipart(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            cc_email=None,
            bcc_email=None,
            subject=subject,
            plain_body=None,
            html_body=TEST_MSG_BODY_PREFIX_HTML,
            attachment=None,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

        # get message details
        msg = imap.fetch_message_details(msg_arrived)
        assert msg, 'expected message to have been fetched'
        assert msg.is_multipart(), 'expectected message to be multi-part'

        # now walk through and verify content is html
        msg_part = 0
        for part in msg.walk():
            msg_part += 1
            if msg_part == 1:
                # message top-level
                assert CONTENT_TYPE_MULTI_MIXED in part['Content-Type'], (
                    'expected top-level msg content type to be correct'
                )

            elif msg_part == 2:
                # message content
                assert part['Content-Type'] == CONTENT_TYPE_TEXT_HTML, 'expected msg content type to be correct'
                break

    def test_send_email_multipart(self, smtp, imap):
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send multipart text and html {datetime.datetime.now()}'
        send_exception = smtp.send_test_email_multipart(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            cc_email=None,
            bcc_email=None,
            subject=subject,
            plain_body=TEST_MSG_BODY_PREFIX,
            html_body=TEST_MSG_BODY_PREFIX_HTML,
            attachment=None,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

        # get message details
        msg = imap.fetch_message_details(msg_arrived)
        assert msg, 'expected message to have been fetched'
        assert msg.is_multipart(), 'expectected message to be multi-part'

        # now walk through and verify content is html
        msg_part = 0
        for part in msg.walk():
            msg_part += 1
            if msg_part == 1:
                # message top-level
                assert CONTENT_TYPE_MULTI_MIXED in part['Content-Type'], (
                    'expected top-level msg content type to be correct'
                )

            elif msg_part == 2:
                # plain text message content
                assert CONTENT_TYPE_TEXT_PLAIN_ASCII in part['Content-Type'], 'expected msg content type to be correct'

            elif msg_part == 3:
                # html message content
                assert part['Content-Type'] == CONTENT_TYPE_TEXT_HTML, 'expected msg content type to be correct'
                break

    def test_send_email_multipart_with_attachment(self, smtp, imap):
        subject = (
            f'{TEST_MSG_SUBJECT_PREFIX} SMTP send multipart text and html with attachment {datetime.datetime.now()}'
        )
        send_exception = smtp.send_test_email_multipart(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            cc_email=None,
            bcc_email=None,
            subject=subject,
            plain_body=TEST_MSG_BODY_PREFIX,
            html_body=TEST_MSG_BODY_PREFIX_HTML,
            attachment=TEST_MSG_ATTACHMENT,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

        # get message details
        msg = imap.fetch_message_details(msg_arrived)
        assert msg, 'expected message to have been fetched'
        assert msg.is_multipart(), 'expectected message to be multi-part'

        # now walk through and verify content is html
        msg_part = 0
        for part in msg.walk():
            msg_part += 1
            if msg_part == 1:
                # message top-level
                assert CONTENT_TYPE_MULTI_MIXED in part['Content-Type'], (
                    'expected top-level msg content type to be correct'
                )

            elif msg_part == 2:
                # text body
                assert part['Content-Type'] == CONTENT_TYPE_TEXT_PLAIN_ASCII, 'expected msg content type to be correct'

            elif msg_part == 3:
                # html body
                # DEBUG:mailstrom-tests:Content-Type: text/html; charset="us-ascii"
                assert part['Content-Type'] == CONTENT_TYPE_TEXT_HTML, 'expected msg content type to be correct'

            elif msg_part == 4:
                # attachment
                exp_type = f'{CONTENT_TYPE_PNG}; name="{os.path.basename(TEST_MSG_ATTACHMENT)}"'
                assert part['Content-Type'] == exp_type, 'expected msg content type to be correct'

                # actually download the attachment
                download_to = DOWNLOAD_EMAIL_ATTACHMENTS_PATH + 'smtp-multipart-msg-test-download.png'
                log.debug(f'downloading email msg attachment to: {download_to} ')
                try:
                    with open(download_to, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                except Exception as e:
                    log.debug(f'{str(e)}')

                assert os.path.isfile(download_to), 'expected downloaded file to exist'

                # compare the dowloaded file with the file that was attached when the email was originally sent
                og_stats = os.stat(TEST_MSG_ATTACHMENT)
                df_stats = os.stat(download_to)
                assert df_stats.st_size == og_stats.st_size, (
                    'expected downloaded attachment size to match original file size'
                )
                assert df_stats.st_ctime > og_stats.st_ctime, (
                    'expected downlaoded attachment ctime to be > original file ctime'
                )

    def test_send_email_with_cc(self, smtp, imap):
        # send email from self to self and cc other
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test with cc {datetime.datetime.now()}'
        send_exception = smtp.send_test_email_multipart(
            to_email=TEST_ACCT_2_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            cc_email=TEST_ACCT_1_EMAIL,
            bcc_email=None,
            subject=subject,
            plain_body=None,
            html_body=TEST_MSG_BODY_PREFIX,
            attachment=None,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

        # todo: fetch message and ensure TEST_ACCT_1_EMAIL is cc'd
        msg = imap.fetch_message_details(msg_arrived)
        assert msg, 'expected message to have been fetched'
        assert msg['From'] == TEST_ACCT_2_EMAIL, 'expected recevied message to have correct from address'
        assert msg['To'] == TEST_ACCT_2_EMAIL, 'expected recevied message to have correct to address'
        assert msg['CC'] == TEST_ACCT_1_EMAIL, 'expected recevied message to have correct CC address'

    def test_send_email_with_bcc(self, smtp, imap):
        # send email from self to self and bcc other
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test with bcc {datetime.datetime.now()}'
        send_exception = smtp.send_test_email_multipart(
            to_email=TEST_ACCT_2_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            cc_email=None,
            bcc_email=TEST_ACCT_1_EMAIL,
            subject=subject,
            plain_body=None,
            html_body=TEST_MSG_BODY_PREFIX,
            attachment=None,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

        # todo: fetch message and ensure TEST_ACCT_1_EMAIL is cc'd
        msg = imap.fetch_message_details(msg_arrived)
        assert msg, 'expected message to have been fetched'
        assert msg['From'] == TEST_ACCT_2_EMAIL, 'expected recevied message to have correct from address'
        assert msg['To'] == TEST_ACCT_2_EMAIL, 'expected recevied message to have correct to address'
        assert msg['BCC'] == TEST_ACCT_1_EMAIL, 'expected recevied message to have correct BCC address'

    def test_send_email_with_priority_flag(self, smtp, imap):
        subject = f'{TEST_MSG_SUBJECT_PREFIX} SMTP send test with priority flag {datetime.datetime.now()}'
        send_exception = smtp.send_test_email_multipart(
            to_email=TEST_ACCT_1_EMAIL,
            from_email=TEST_ACCT_2_EMAIL,
            cc_email=None,
            bcc_email=None,
            subject=subject,
            plain_body=None,
            html_body=TEST_MSG_BODY_PREFIX,
            attachment=None,
            priority=True,
        )
        assert send_exception is None, 'expected send message to be successful'

        # now use imap and check if the sent message was received
        msg_arrived = imap.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL[:3]}***'

        # fetch message and verify priority flag set
        msg = imap.fetch_message_details(msg_arrived)
        assert msg, 'expected message to have been fetched'
        assert msg['X-Priority'] == '1', 'expected recevied message to have priority flag set'
