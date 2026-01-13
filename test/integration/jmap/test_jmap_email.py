import pytest

from datetime import datetime, timedelta, timezone
from jmapc import EmailQueryFilterCondition
from common.utils import verify_jmap_test_email

from common.const import (
    TEST_MSG_SUBJECT_PREFIX,
    TEST_MSG_BODY_PREFIX,
    TEST_MSG_BODY_PREFIX_HTML,
)

from const import (
    TEST_ACCT_1_EMAIL,
    TEST_ACCT_2_EMAIL,
)


@pytest.mark.usefixtures('populate_inbox')
class TestJMAPEmail:
    def test_query_email_all(self, jmap_acct_1):
        # our populate inbox fixture ensures that email already exists in our TEST_ACCT_1 inbox and drafts
        email_ids = jmap_acct_1.query_email()
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_inbox(self, jmap_acct_1):
        # our populate inbox fixture ensures that email already exists in our TEST_ACCT_1 inbox, so query
        # for all email in the inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        filter = EmailQueryFilterCondition(in_mailbox=inbox_id)
        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_drafts(self, jmap_acct_1):
        # our populate inbox fixture ensures that draft emails already exists in our TEST_ACCT_1 drafts folder
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Drafts')
        draft_mailbox_id = mailbox_search[0].id
        assert draft_mailbox_id, 'expected to get the draft mailbox id'

        filter = EmailQueryFilterCondition(in_mailbox=draft_mailbox_id)
        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_limit(self, jmap_acct_1):
        # our populate inbox fixture ensures that email already exists in our TEST_ACCT_1 inbox and drafts
        query_limit = 3
        email_ids = jmap_acct_1.query_email(limit=query_limit)
        assert len(email_ids) == query_limit, 'expected the email query results to be limited to 3 emails'

    def test_query_email_filter_subject(self, jmap_acct_1):
        # our populate inbox fixture ensures that email already exists in our TEST_ACCT_1 inbox with the email
        # subjects starting with TEST_MSG_SUBJECT_PREFIX; so query for email in the inbox with that subject
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        search_filter = {
            'inMailbox': inbox_id,
            'subject': TEST_MSG_SUBJECT_PREFIX,
        }

        email_ids = jmap_acct_1.query_email(filter=search_filter)
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_filter_body(self, jmap_acct_1):
        # our populate inbox fixture ensures that email already exists in our TEST_ACCT_1 inbox with the email
        # body starting with TEST_MSG_BODY_PREFIX; so query for email in the inbox with that subject
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        filter = EmailQueryFilterCondition(in_mailbox=inbox_id, body=TEST_MSG_BODY_PREFIX)
        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_filter_body_not_found(self, jmap_acct_1):
        # search emails in inbox that have some body text that we know doesn't exist in an email
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        filter = EmailQueryFilterCondition(in_mailbox=inbox_id, body='238y$@!!3445000-7345@#$134@#$%349')
        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) == 0, 'expected zero email ids to be returned'

    def test_query_email_filter_from(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        filter = EmailQueryFilterCondition(in_mailbox=inbox_id, mail_from=TEST_ACCT_2_EMAIL)
        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_filter_from_not_found(self, jmap_acct_1):
        # query emails from an email address that we know doesn't exist in our inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        filter = EmailQueryFilterCondition(in_mailbox=inbox_id, mail_from='189#$%$#$^#%@fake.com')
        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) == 0, 'expected zero email ids to have been returned'

    def test_query_email_filter_to(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        filter = EmailQueryFilterCondition(in_mailbox=inbox_id, to=TEST_ACCT_1_EMAIL)
        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_filter_before_date(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        # query for email received before a date in the future, so we know for sure email will be found
        filter = EmailQueryFilterCondition(
            in_mailbox=inbox_id, before=datetime.now(tz=timezone.utc) + timedelta(days=7)
        )

        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) >= 1, 'expected at least 1 email id to be returned'

    def test_query_email_filter_before_date_not_found(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        # query for email received before a date years ago (that we know won't return any email)
        filter = EmailQueryFilterCondition(
            in_mailbox=inbox_id,
            before=datetime(1994, 8, 24, 12, 1, 2, tzinfo=timezone.utc),
        )

        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) == 0, 'expected zero email ids to be returned'

    def test_query_email_filter_after_date(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        # query for email received within the last 7 days
        filter = EmailQueryFilterCondition(
            in_mailbox=inbox_id,
            after=datetime.now(tz=timezone.utc) - timedelta(days=7),
        )

        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) >= 1, 'expected at least one email id to be returned'

    def test_query_email_filter_after_date_not_found(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        mailbox_search = jmap_acct_1.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        # query email received after a date in the future so we know none will be found
        filter = EmailQueryFilterCondition(
            in_mailbox=inbox_id,
            after=datetime.now(tz=timezone.utc) + timedelta(days=365),
        )

        email_ids = jmap_acct_1.query_email(filter)
        assert len(email_ids) == 0, 'expected zero email ids to be returned'

    def test_get_email_single(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        # query to get email ids from the inbox and then retrieve one of the actual emails
        test_email_id = jmap_acct_1.get_test_email_ids_from_inbox()[0]
        found_emails, not_found_emails = jmap_acct_1.get_email([test_email_id])

        assert found_emails, 'expected get email to have returned an email'
        assert not_found_emails is None, 'expected get email to return no not_found emails'

        ret_email = found_emails[0]

        # verify data in the fetched email
        verify_jmap_test_email(
            email=ret_email,
            expected_values={
                'id': test_email_id,
                'mailbox_id': 'a',
                'from_email': TEST_ACCT_2_EMAIL,
                'to_email': TEST_ACCT_1_EMAIL,
                'subject_prefix': TEST_MSG_SUBJECT_PREFIX,
                'body_prefix': TEST_MSG_BODY_PREFIX,
                'has_attachment': False,
            },
        )

    def test_get_email_id_not_exist(self, jmap_acct_1):
        # attempt to get an email using an id that doesn't exist, expect email not found response
        fake_id = '999999'
        found_emails, not_found_emails = jmap_acct_1.get_email([fake_id])

        assert not_found_emails, 'expected not found email id to have been returned'
        assert found_emails is None, 'expected no found emails to have been returned'
        assert not_found_emails[0] == fake_id, 'expected not found email id to match'

    def test_get_email_multi(self, jmap_acct_1):
        # our populate inbox fixture ensures that an email already exists in our TEST_ACCT_1 inbox
        # query to get email ids from the inbox and then retrieve three of the emails
        test_email_ids = jmap_acct_1.get_test_email_ids_from_inbox()
        found_emails, not_found_emails = jmap_acct_1.get_email(test_email_ids[:3])

        assert found_emails, 'expected get email to have returned emails'
        assert not_found_emails is None, 'expected get email to return no not_found emails'
        assert len(found_emails) == 3, 'expected get email to return data for 3 emails'

        # verify data in each of the fetched emails
        for index, email in enumerate(found_emails):
            verify_jmap_test_email(
                email=email,
                expected_values={
                    'id': test_email_ids[index],
                    'mailbox_id': 'a',
                    'from_email': TEST_ACCT_2_EMAIL,
                    'to_email': TEST_ACCT_1_EMAIL,
                    'subject_prefix': TEST_MSG_SUBJECT_PREFIX,
                    'body_prefix': TEST_MSG_BODY_PREFIX,
                    'has_attachment': False,
                },
            )

    def test_create_draft_email(self, jmap_acct_2):
        # create a draft email and confirm it was created
        subject = f'{TEST_MSG_SUBJECT_PREFIX} JMAP draft email test {datetime.now()}'

        draft_email_id = jmap_acct_2.create_draft_email(
            from_email=TEST_ACCT_2_EMAIL,
            to_email=TEST_ACCT_1_EMAIL,
            subject=subject,
            plain_text_body=TEST_MSG_BODY_PREFIX,
        )

        assert draft_email_id, 'expected to be able to successfully create a draft email'

        # now verify the draft email was created
        found_emails, not_found_emails = jmap_acct_2.get_email([draft_email_id])
        draft_email = found_emails[0]
        assert draft_email.mailbox_ids == {'d': True}, 'expected draft email to be in drafts folder'

    def test_send_email_plain_text(self, jmap_acct_1, jmap_acct_2):
        # create and send a new email from TEST_ACCT_2_EMAIL to TEST_ACCT_1_EMAIL
        subject = f'{TEST_MSG_SUBJECT_PREFIX} JMAP send test {datetime.now()}'

        result = jmap_acct_2.send_email(
            from_email=TEST_ACCT_2_EMAIL,
            to_email=TEST_ACCT_1_EMAIL,
            subject=subject,
            plain_text_body=TEST_MSG_BODY_PREFIX,
        )

        assert result, 'expected to be able to successfully send an email'

        # now wait for the message to arrive at TEST_ACCT_1 (poll if necessary)
        msg_arrived = jmap_acct_1.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL.split("@")[0]}'

    def test_send_email_html(self, jmap_acct_1, jmap_acct_2):
        # send an email with html body content
        subject = f'{TEST_MSG_SUBJECT_PREFIX} JMAP send HTML test {datetime.now()}'

        result = jmap_acct_2.send_email(
            from_email=TEST_ACCT_2_EMAIL,
            to_email=TEST_ACCT_1_EMAIL,
            subject=subject,
            html_body=TEST_MSG_BODY_PREFIX_HTML,
        )

        assert result, 'expected to be able to successfully send an email with html body content'

        # now wait for the message to arrive at TEST_ACCT_1 (poll if necessary)
        msg_arrived = jmap_acct_1.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_1_EMAIL.split("@")[0]}'

    def test_send_email_with_cc(self, jmap_acct_1, jmap_acct_2):
        # send an email from TEST_ACCT_2 to self and cc TEST_ACCT_1
        subject = f'{TEST_MSG_SUBJECT_PREFIX} JMAP send test with cc {datetime.now()}'

        result = jmap_acct_2.send_email(
            from_email=TEST_ACCT_2_EMAIL,
            to_email=TEST_ACCT_2_EMAIL,
            subject=subject,
            cc_email=TEST_ACCT_1_EMAIL,
            plain_text_body=TEST_MSG_BODY_PREFIX,
        )

        assert result, 'expected to be able to successfully send an email with cc'

        # now wait for the message to arrive at TEST_ACCT_2 (poll if necessary)
        msg_arrived = jmap_acct_2.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_2_EMAIL.split("@")[0]}'
        # todo

        # now wait for the cc'd message to arrive at TEST_ACCT_1 (poll if necessary)
        msg_arrived = jmap_acct_1.wait_for_message_to_arrive(subject)
        assert msg_arrived, f"expected the sent cc'd message to have arrived at {TEST_ACCT_1_EMAIL.split('@')[0]}"
        # todo

    def test_send_email_with_bcc(self, jmap_acct_1, jmap_acct_2):
        # send an email from TEST_ACCT_2 to self and bcc TEST_ACCT_1
        subject = f'{TEST_MSG_SUBJECT_PREFIX} JMAP send test with bcc {datetime.now()}'

        result = jmap_acct_2.send_email(
            from_email=TEST_ACCT_2_EMAIL,
            to_email=TEST_ACCT_2_EMAIL,
            subject=subject,
            bcc_email=TEST_ACCT_1_EMAIL,
            plain_text_body=TEST_MSG_BODY_PREFIX,
        )

        assert result, 'expected to be able to successfully send an email with bcc'

        # now wait for the message to arrive at TEST_ACCT_2 (poll if necessary)
        msg_arrived = jmap_acct_2.wait_for_message_to_arrive(subject)
        assert msg_arrived, f'expected the sent message to have arrived at {TEST_ACCT_2_EMAIL.split("@")[0]}'

        # now wait for the cc'd message to arrive at TEST_ACCT_1 (poll if necessary)
        msg_arrived = jmap_acct_1.wait_for_message_to_arrive(subject)
        assert msg_arrived, f"expected the sent bcc'd message to have arrived at {TEST_ACCT_1_EMAIL.split('@')[0]}"
