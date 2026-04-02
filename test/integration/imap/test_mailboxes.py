import datetime
import pytest

from common.logger import log
from common.utils import convert_raw_mailbox_list

from common.const import (
    RESULT_NO,
    ALREADY_EXISTS,
    MISSING_ARGS,
    NOT_FOUND,
    MAILBOX_PREFIX,
    MAILBOX_ALREADY_SUBSCRIBED,
    MAILBOX_NAME_MISSING,
    MAILBOX_NOT_EXIST,
    MAILBOX_ALREADY_UNSUBSCRIBED,
    INVALID_FOLDER_NAME,
    MAILBOX_HAS_CHILD,
    STATE_SELECTED,
    STATE_AUTH,
    RESULT_OK,
    MAILBOX_CLOSE_ILLEGAL_STATE,
)

from const import (
    DEFAULT_IMAP_MAILBOX_LIST,
)


class TestIMAPMailboxes:
    """
    IMAP mailbox (folders) tests.
    """

    def test_list_all_mailboxes(self, imap):
        mailbox_list = imap.get_mailboxes()
        # ensure that the expected default malboxes exist
        for expected_mailbox in DEFAULT_IMAP_MAILBOX_LIST:
            assert expected_mailbox in mailbox_list, 'expected default mailboxes to exist'

    @pytest.mark.sanity
    def test_create_mailbox(self, imap):
        # create and subscribe to unique mailbox
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(name)
        imap.subscribe_mailbox(name)
        # verify new mailbox was created
        assert imap.do_mailboxes_exist([name]), f'expected mailbox {name} to exist'

    def test_create_one_sub_mailbox(self, imap):
        # create and subscribe to root-level mailbox
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(name)
        imap.subscribe_mailbox(name)

        # now create a mailbox one level down from the other (i.e. subfolder)
        sub_name = f'{name}/{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(sub_name)
        imap.subscribe_mailbox(sub_name)

        # verify new mailbox was created
        assert imap.do_mailboxes_exist([sub_name]), f'expected mailbox {name} to exist'

    def test_create_multi_sub_mailboxes_one_command(self, imap):
        # create 10 hierarchical levels of mailboxes in one create command, and verify
        name_string = ''
        new_mailboxes = []

        for level in range(1, 11):
            next_mailbox = f'{MAILBOX_PREFIX} {level} {datetime.datetime.now()}'
            # append the level separator to start of name for all subfolders
            name_string += f'/{next_mailbox}' if level > 1 else f'{next_mailbox}'
            new_mailboxes.append(name_string)

        imap.create_mailbox(name_string)

        # subscribe to each new mailbox
        for mailbox in new_mailboxes:
            imap.subscribe_mailbox(mailbox)

        # now verify all were created
        assert imap.do_mailboxes_exist(new_mailboxes)

    def test_create_mailbox_already_exists(self, imap):
        # create and subscribe to root-level mailbox
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(name)
        imap.subscribe_mailbox(name)

        # attempt to create another mailbox with the same name
        log.debug(f'attempting to create mailbox with same name: {name}')
        result, data = imap.connection.create(f'"{name}"')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected status of NO when attempt to create mailbox that already exists'
        assert ALREADY_EXISTS in data[0], 'expected mailbox already exists message'

    def test_create_mailbox_invalid_name(self, imap):
        # attempt to create mailbox with invalid name
        log.debug('attempting to create mailbox with invalid name')
        result, data = imap.connection.create(' ')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected status of NO when attempt to create mailbox that already exists'
        assert MISSING_ARGS in data[0], 'expected missing arguments message'

    @pytest.mark.sanity
    def test_subscribe_mailbox(self, imap):
        new_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(new_mailbox)
        # verify new mailbox is not subscribed by default
        assert not imap.are_mailboxes_subscribed([new_mailbox]), 'expected mailbox NOT to be subscribed to'
        # subscribe and verify
        imap.subscribe_mailbox(new_mailbox)
        assert imap.are_mailboxes_subscribed([new_mailbox]), 'expected mailbox to be subscribed to'

    def test_subscribe_mailbox_already_subscribed(self, imap):
        new_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(new_mailbox)
        # subscribe and verify
        imap.subscribe_mailbox(new_mailbox)
        assert imap.are_mailboxes_subscribed([new_mailbox]), 'expected mailbox to be subscribed to'

        # attempt to subscribe again, expect not
        log.debug(f'attempting to subscribe to the same mailbox again: {new_mailbox}')
        result, data = imap.connection.subscribe(f'"{new_mailbox}"')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected subscribe to return NO'
        assert MAILBOX_ALREADY_SUBSCRIBED in data[0], 'expected already subscribed message'

    def test_subscribe_mailbox_no_exist(self, imap):
        # attempt to subscribe to mailbox that does not exist
        log.debug('attempting to subscribe to mailbox that does not exist')
        result, data = imap.connection.subscribe('Nope')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected status of NO when attempt to subscribe to mailbox that does not exist'
        assert MAILBOX_NOT_EXIST in data[0], 'expected mailbox does not exist message'

    def test_subscribe_mailbox_no_name(self, imap):
        # attempt to subscribe to mailbox with no name
        log.debug('attempting to subscribe to mailbox with no name')
        result, data = imap.connection.subscribe(' ')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected status of NO when attempt to subscribe to mailbox with no name'
        assert MAILBOX_NAME_MISSING in data[0], 'expected missing mailbox name message'

    def test_unsubscribe_mailbox(self, imap):
        new_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(new_mailbox)
        # subscribe and verify
        imap.subscribe_mailbox(new_mailbox)
        assert imap.are_mailboxes_subscribed([new_mailbox]), 'expected mailbox to be subscribed to'
        # now unsubscribe and verify
        imap.unsubscribe_mailbox(new_mailbox)
        assert not imap.are_mailboxes_subscribed([new_mailbox]), 'expected mailbox NOT to be subscribed to'

    def test_unsubscribe_mailbox_already_unsubscribed(self, imap):
        new_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(new_mailbox)
        # verify new mailbox is not subscribed by default
        assert not imap.are_mailboxes_subscribed([new_mailbox]), 'expected mailbox NOT to be subscribed to'

        # attempt to unsubscribe when not subscribed, expect not
        log.debug(f'attempting to unsubscribe mailbox that is already unsubscribed: {new_mailbox}')
        result, data = imap.connection.unsubscribe(f'"{new_mailbox}"')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected subscribe to return NO'
        assert MAILBOX_ALREADY_UNSUBSCRIBED in data[0], 'expected already unsubscribed message'

    def test_unsubscribe_mailbox_no_exist(self, imap):
        # attempt to unsubscribe to mailbox that does not exist
        log.debug('attempting to unsubscribe a mailbox that does not exist')
        result, data = imap.connection.unsubscribe('Nope')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected status of NO when attempt to unsubscribe a mailbox that does not exist'
        assert MAILBOX_NOT_EXIST in data[0], 'expected mailbox does not exist message'

    def test_unsubscribe_mailbox_no_name(self, imap):
        # attempt to unsubscribe to mailbox with no name
        log.debug('attempting to unsubscribe a mailbox with no name')
        result, data = imap.connection.unsubscribe(' ')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected status of NO when attempt to unsubscribe a mailbox with no name'
        assert MAILBOX_NAME_MISSING in data[0], 'expected missing mailbox name message'

    def test_rename_mailbox(self, imap):
        # create and then rename a mailbox
        old_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(old_name)
        imap.subscribe_mailbox(old_name)

        new_name = f'{MAILBOX_PREFIX} RENAMED! {datetime.datetime.now()}'
        imap.rename_mailbox(old_name, new_name)

        assert imap.do_mailboxes_exist([new_name]), 'expected renamed mailbox to exist'
        assert imap.do_mailboxes_exist([old_name]) is False, 'expected old mailbox not to exist'

    def test_rename_sub_mailbox(self, imap):
        # create a mailbox that has a subfolder/mailbox
        first_mailbox = f'{MAILBOX_PREFIX} ONE {datetime.datetime.now()}'
        second_mailbox = f'{first_mailbox}/{MAILBOX_PREFIX} TWO {datetime.datetime.now()}'

        # create two mailboxes in one command (folder with a subfolder)
        imap.create_mailbox(second_mailbox)
        imap.subscribe_mailbox(first_mailbox)
        imap.subscribe_mailbox(second_mailbox)
        assert imap.do_mailboxes_exist([first_mailbox, second_mailbox]), 'expected both mailboxes to exist'

        # now rename the subfolder
        new_name = f'{first_mailbox}/{MAILBOX_PREFIX} RENAMED! {datetime.datetime.now()}'
        imap.rename_mailbox(second_mailbox, new_name)

        assert imap.do_mailboxes_exist([new_name, first_mailbox]) is True, 'expected mailboxes to exist'
        assert imap.do_mailboxes_exist([second_mailbox]) is False, 'expected old mailbox not to exist'

    def test_rename_mailbox_to_existing_name(self, imap):
        # attempt to rename a mailbox to the name of a mailbox that already exists
        first_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(first_mailbox)
        imap.subscribe_mailbox(first_mailbox)

        second_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(second_mailbox)
        imap.subscribe_mailbox(second_mailbox)

        log.debug(f'attempting to rename mailbox: {first_mailbox} to the name of existing mailbox: {second_mailbox}')
        result, data = imap.connection.rename(f'"{first_mailbox}"', f'"{second_mailbox}"')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected rename to return NO'
        assert ALREADY_EXISTS in data[0], 'expected not found message'
        assert imap.do_mailboxes_exist([first_mailbox, second_mailbox]) is True, (
            'expected both mailboxes to still exist'
        )

    def test_rename_mailbox_no_exist(self, imap):
        # attempt to rename a mailbox that doesn't exist
        no_exist = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        new_name = f'{MAILBOX_PREFIX} RENAMED! {datetime.datetime.now()}'

        log.debug('attempting to rename a mailbox that does not exist')
        result, data = imap.connection.rename(f'"{no_exist}"', f'"{new_name}"')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected rename to return NO'
        assert NOT_FOUND in data[0], 'expected not found message'
        assert imap.do_mailboxes_exist([new_name]) is False, 'expected new mailbox name not to exist'

    def test_rename_mailbox_to_invalid_name(self, imap):
        # attempt to rename a mailbox to an invalid name
        old_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(old_name)
        imap.subscribe_mailbox(old_name)

        new_name = ' '
        log.debug(f'attempting to rename mailbox: {old_name} to an invalid name')
        result, data = imap.connection.rename(f'"{old_name}"', f'"{new_name}"')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected rename to return NO'
        assert INVALID_FOLDER_NAME in data[0], 'expected not found message'
        assert imap.do_mailboxes_exist([new_name]) is False, 'expected new mailbox name not to exist'

    def test_delete_mailbox(self, imap):
        # create then delete a mailbox
        test_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(test_mailbox)
        imap.subscribe_mailbox(test_mailbox)
        assert imap.do_mailboxes_exist([test_mailbox]), f'expected mailbox {test_mailbox} to exist'

        imap.delete_mailbox(test_mailbox)
        assert not imap.do_mailboxes_exist([test_mailbox]), f'expected mailbox {test_mailbox} to not exist'

    def test_delete_mailbox_no_exist(self, imap):
        # attempt to delete a mailbox that doesn't exist
        log.debug('attempting to delete a mailbox that does not exist')
        result, data = imap.connection.delete('"Nope this mailbox does not exist"')
        log.debug(f'{result}, {data}')
        assert result == RESULT_NO, 'expected delete to return NO'
        assert MAILBOX_NOT_EXIST in data[0], 'expected mailbox does not exist error'

    def test_delete_sub_mailbox(self, imap):
        # create a mailbox that has a subfolder/mailbox
        first_mailbox = f'{MAILBOX_PREFIX} ONE {datetime.datetime.now()}'
        second_mailbox = f'{first_mailbox}/{MAILBOX_PREFIX} TWO {datetime.datetime.now()}'

        # create two mailboxes in one command (folder with a subfolder)
        imap.create_mailbox(second_mailbox)
        imap.subscribe_mailbox(first_mailbox)
        imap.subscribe_mailbox(second_mailbox)
        assert imap.do_mailboxes_exist([first_mailbox, second_mailbox]), 'expected both mailboxes to exist'

        # now delete the subfolder and verify
        imap.delete_mailbox(second_mailbox)
        assert imap.do_mailboxes_exist([first_mailbox]) is True, 'expected first mailbox to exist'
        assert imap.do_mailboxes_exist([second_mailbox]) is False, 'expected sub mailbox not to exist'

    def test_delete_mailbox_containing_child(self, imap):
        # create a mailbox that has a subfolder/mailbox
        first_mailbox = f'{MAILBOX_PREFIX} ONE {datetime.datetime.now()}'
        second_mailbox = f'{first_mailbox}/{MAILBOX_PREFIX} TWO {datetime.datetime.now()}'

        # create two mailboxes in one command (folder with a subfolder)
        imap.create_mailbox(second_mailbox)
        imap.subscribe_mailbox(first_mailbox)
        imap.subscribe_mailbox(second_mailbox)
        assert imap.do_mailboxes_exist([first_mailbox, second_mailbox]), 'expected both mailboxes to exist'

        # now attempt to delete the parent folder, expect not
        log.debug(f'attempting to delete mailbox that contains a child mailbox: {first_mailbox}')
        result, data = imap.connection.delete(f'"{first_mailbox}"')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected delete to return NO'
        assert MAILBOX_HAS_CHILD in data[0], 'expected mailbox contains child error message'

        assert imap.do_mailboxes_exist([first_mailbox, second_mailbox]) is True, 'expected both mailboxes to exist'

    def test_select_mailbox_default(self, imap):
        # first ensure no mailbox is currently selected
        imap.unselect_mailbox()

        # select mailbox but don't provide a name, should select INBOX by default
        imap.select_mailbox()

        # now verify we are in selected state
        log.debug(f'verifying connection state is: {STATE_SELECTED}')
        assert imap.connection.state == STATE_SELECTED

    def test_select_specific_mailbox(self, imap):
        # first ensure no mailbox is currently selected
        imap.unselect_mailbox()

        # select a specific mailbox
        test_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(test_mailbox)
        imap.subscribe_mailbox(test_mailbox)

        imap.select_mailbox(test_mailbox)

        # now verify we are in selected state
        log.debug(f'verifying connection state is: {STATE_SELECTED}')
        assert imap.connection.state == STATE_SELECTED

    def test_select_sub_mailbox(self, imap):
        # first ensure no mailbox is currently selected
        imap.unselect_mailbox()

        # create a mailbox that has a subfolder/mailbox
        first_mailbox = f'{MAILBOX_PREFIX} ONE {datetime.datetime.now()}'
        second_mailbox = f'{first_mailbox}/{MAILBOX_PREFIX} TWO {datetime.datetime.now()}'

        # create two mailboxes in one command (folder with a subfolder)
        imap.create_mailbox(second_mailbox)
        imap.subscribe_mailbox(first_mailbox)
        imap.subscribe_mailbox(second_mailbox)
        assert imap.do_mailboxes_exist([first_mailbox, second_mailbox]), 'expected both mailboxes to exist'

        # now select the subfolder
        imap.select_mailbox(second_mailbox)

        log.debug(f'verifying connection state is: {STATE_SELECTED}')
        assert imap.connection.state == STATE_SELECTED

    def test_select_mailbox_no_exist(self, imap):
        # first ensure no mailbox is currently selected
        imap.unselect_mailbox()

        # attempt to select a mailbox that doesn't exist, expect not
        result, data = imap.connection.select('"This mailbox does not exist!"')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected select to return NO'
        assert MAILBOX_NOT_EXIST in data[0], 'expected mailbox does not exist message'

        log.debug(f'verifying connection state is still: {STATE_AUTH}')
        assert imap.connection.state == STATE_AUTH

    def test_select_mailbox_no_name(self, imap):
        # first ensure no mailbox is currently selected
        imap.unselect_mailbox()

        # attempt to select a mailbox with no name
        result, data = imap.connection.select(' ')
        log.debug(f'{result}, {data}')

        assert result == RESULT_NO, 'expected select to return NO'
        assert MAILBOX_NAME_MISSING in data[0], 'expected mailbox name missing message'

        log.debug(f'verifying connection state is still: {STATE_AUTH}')
        assert imap.connection.state == STATE_AUTH

    def test_unselect_mailbox(self, imap):
        # if a mailbox isn't currently selected, select the INBOX
        if imap.connection.state != STATE_SELECTED:
            imap.select_mailbox()

        log.debug(f'verifying connection state is: {STATE_SELECTED}')
        assert imap.connection.state == STATE_SELECTED

        # unselect (which also verifies state is back to AUTH)
        imap.unselect_mailbox()

    def test_list_subscribed_mailboxes(self, imap):
        # create and subscribe to a mailbox so we know there's at least one subscribed
        test_mailbox = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        imap.create_mailbox(test_mailbox)
        imap.subscribe_mailbox(test_mailbox)

        # now list subscribed mailboxes and verify our new one is listed
        assert imap.are_mailboxes_subscribed([test_mailbox]), 'expected mailbox to be subscribed to'

    def test_list_mailboxes_pattern(self, imap):
        # create and subscribe to a mailbox with specific name that will match our pattern
        first_mailbox = f'{MAILBOX_PREFIX} YES! {datetime.datetime.now()}'
        imap.create_mailbox(first_mailbox)
        imap.subscribe_mailbox(first_mailbox)

        # create and subscribe to a mailbox with name that won't match our pattern
        second_mailbox = f'{MAILBOX_PREFIX} NO! {datetime.datetime.now()}'
        imap.create_mailbox(second_mailbox)
        imap.subscribe_mailbox(second_mailbox)

        # now list mailboxes with pattern
        log.debug(f'getting list of mailboxes with pattern: {MAILBOX_PREFIX} YES!*')
        result, data = imap.connection.list(f'"{MAILBOX_PREFIX} YES!*"')
        log.debug(f'{result}, {data}')
        assert result == RESULT_OK, 'expected list with pattern to return OK'
        assert data[0] is not None, 'expected list of mailboxes to be returned in data'

        pretty_mailbox_list = convert_raw_mailbox_list(data)

        # now verify that our first mailbox (that matches pattern) is in the list returned
        # and that our second mailbox (that doesn't match the pattern) is not in the list
        first_mailbox_found = False
        for mailbox in pretty_mailbox_list:
            if mailbox['name'] == second_mailbox:
                assert False, 'expected our second mailbox name not to be in the list returned'
            if mailbox['name'] == first_mailbox:
                first_mailbox_found = True
        assert first_mailbox_found, 'expected first mailbox name to be in the list returned'

    def test_close_mailbox(self, imap):
        # if a mailbox isn't currently selected, select the INBOX
        if imap.connection.state != STATE_SELECTED:
            imap.select_mailbox()

        log.debug(f'verifying connection state is: {STATE_SELECTED}')
        assert imap.connection.state == STATE_SELECTED

        # now close the mailbox
        imap.close_mailbox()

        log.debug(f'verifying connection state is: {STATE_AUTH}')
        assert imap.connection.state == STATE_AUTH

    def test_close_mailbox_none_selected(self, imap):
        # if a mailbox is selected, unselect
        if imap.connection.state == STATE_SELECTED:
            imap.unselect_mailbox()

        log.debug(f'verifying connection state is: {STATE_AUTH}')
        assert imap.connection.state == STATE_AUTH

        # now attempt to close mailbox, expect err
        log.debug('attempting to close mailbox when none is selected')
        try:
            imap.connection.close()
        except Exception as e:
            log.debug(f'{str(e)}')
            assert MAILBOX_CLOSE_ILLEGAL_STATE in str(e)
