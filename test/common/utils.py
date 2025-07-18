from common.logger import log
from datetime import datetime, timezone


def convert_raw_mailbox_list(raw_mailbox_list):
    """
    The data returned from imap.list() is a list of byte strings, each entry being one mailbox.
    One entry mailbox item like this, for example: b'() "/" "INBOX"'
    Convert the list of mailboxes into a nice list of dictionaries, each one like this, for example:
    {'flags': '()', 'separator': '/"', 'name': 'INBOX"'}
    """
    pretty_mailbox_list = []

    if raw_mailbox_list is not None:
        for raw_mailbox in raw_mailbox_list:
            # starts as: b'() "/" "Deleted Items"'
            mailbox = raw_mailbox.decode().split(' ', 2)
            # now looks like: ['()', '"/"', '"Deleted Items"']
            pretty_mailbox_list.append({'flags': mailbox[0], 'separator': mailbox[1], 'name': mailbox[2].strip('"')})
            # was appended like this: {'flags': '()', 'separator': '"/"', 'name': 'Deleted Items'}

    return pretty_mailbox_list


def verify_jmap_test_email(email, expected_values):
    """
    Verify that the given jmap email object has the expected values.
    """
    log.debug(f"verifying data in email id '{email.id}' is correct")
    assert email.id == expected_values['id'], 'expected the fetched email id to be correct'
    assert email.mailbox_ids[expected_values['mailbox_id']], 'expected the fetched email mailbox to be correct'
    assert email.size > 0, 'expected the fetched email size to have a value'

    assert type(email.received_at) is datetime, 'expected fetched email received at to be a datetime object'
    assert email.received_at < datetime.now(tz=timezone.utc), 'expected fetched email received at to be correct'
    assert email.mail_from[0].email == expected_values['from_email'], (
        'expected fetched email from address to be correct'
    )
    assert email.to[0].email == expected_values['to_email'], 'expected fetched email to address to be correct'

    assert expected_values['subject_prefix'] in email.subject, 'expected fetched email subject to be correct'
    assert email.has_attachment is expected_values['has_attachment'], 'expected fetched email to not have attachment'
    assert expected_values['body_prefix'] in email.preview, 'expected fetched email preview to be correct'

    ret_email_text_body = email.text_body[0]
    assert ret_email_text_body, 'expected fetched email to contain text body'
    assert ret_email_text_body.size >= len(expected_values['body_prefix']), (
        'expected fetched email text body size to be correct'
    )
    assert ret_email_text_body.type == 'text/plain', 'expected fetched email text body type to be correct'
    assert ret_email_text_body.charset == 'utf-8', 'expected fetched email text body chrset to be correct'
