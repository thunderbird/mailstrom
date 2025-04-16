# test utils

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
            pretty_mailbox_list.append({ 'flags': mailbox[0], 'separator': mailbox[1], 'name': mailbox[2].strip('"') })
            # was appended like this: {'flags': '()', 'separator': '"/"', 'name': 'Deleted Items'}

    return pretty_mailbox_list
