import datetime

from common.logger import log
from jmapc import MailboxQueryFilterCondition

from common.const import (
    MAILBOX_PREFIX,
)

from const import DEFAULT_JMAP_MAILBOX_LIST, JMAP_DELETE_MAILBOX_WITH_CHILD_ERR


class TestJMAPMailboxes:
    def test_mailbox_query_all(self, jmap_acct_1):
        # query all mailboxes with no params/filters; returns list of mailbox ids
        result = jmap_acct_1.query_mailboxes()
        assert result.ids, 'expected mailbox ids to be returned'
        assert len(result.ids) > 1, 'expected more than 1 mailbox id'

    def test_mailbox_query_all_limit_results(self, jmap_acct_1):
        # query all mailboxes but limit to 3 mailbox ids returned
        limit_to = 3
        result = jmap_acct_1.query_mailboxes({'limit': limit_to})
        assert result.ids, 'expected mailbox ids to be returned'
        assert len(result.ids) == 3, f'expected only {limit_to} mailbox ids'
        assert result.limit == limit_to, f'expected query result limit to be {limit_to}'

    def test_mailbox_query_all_include_total(self, jmap_acct_1):
        # query all mailboxes and include total number of mailboxes found
        result = jmap_acct_1.query_mailboxes({'calculate_total': True})
        log.debug(f'query returned mailbox total: {result.total}')
        assert result.ids, 'expected mailbox ids to be returned'
        assert len(result.ids) > 1, 'expected more than 1 mailbox id'
        assert result.total == len(result.ids), 'expected result total to be correct'

    def test_mailbox_query_filter_name(self, jmap_acct_1):
        # query with filter name inbox; should return one mailbox id
        query_data = {'filter': MailboxQueryFilterCondition(name='Inbox')}

        query_result = jmap_acct_1.query_mailboxes(query_data)
        assert query_result.ids, 'expected mailbox ids to be returned'
        assert len(query_result.ids) == 1, 'expected only 1 mailbox id'
        inbox_id = query_result.ids[0]

        # now get the mailbox details for the returned id and verify it is the inbox
        ret_details = jmap_acct_1.get_mailboxes_by_id([inbox_id])[0]
        assert ret_details.id == inbox_id, 'expected get mailbox to return correct id'
        assert ret_details.name == 'Inbox', 'expected mailbox details to be returned for Inbox'

    def test_get_mailbox(self, jmap_acct_1):
        # get mailbox details for the inbox, and verify; we do this in two requests here because we want to
        # get the mailbox id from the query and also verify the id returned in the mailbox get request matches
        mailbox_to_get = 'Inbox'
        log.debug(f'getting mailbox: {mailbox_to_get}')

        query_data = {'filter': MailboxQueryFilterCondition(name=mailbox_to_get)}
        query_result = jmap_acct_1.query_mailboxes(query_data)
        assert len(query_result.ids) == 1, 'expected mailbox query to find the mailbox'

        inbox_id = query_result.ids[0]
        inbox_details = jmap_acct_1.get_mailboxes_by_id([inbox_id])[0]

        assert inbox_details, 'expected get mailbox to return mailbox details'
        assert inbox_details.id == inbox_id, 'expected mailbox id to be correct'
        assert inbox_details.name == mailbox_to_get, 'expected mailbox name to be correct'
        assert inbox_details.is_subscribed, 'expected mailbox is_subscribed to be true'
        assert inbox_details.role == 'inbox', 'expected mailbox role to be correct'
        assert inbox_details.parent_id is None, 'expected mailbox to have no parent id'

        # for inbox email numbers just verify 0 or above as we don't know if/how many emails exist;
        # the jmap_acct_1_messaging tests will test these return values when emails do exist for certain
        assert inbox_details.total_emails >= 0, 'expected mailbox total emails to be >= 0'
        assert inbox_details.unread_emails >= 0, 'expected mailbox unread emails to be >= 0'
        assert inbox_details.total_threads >= 0, 'expected mailbox total threads to be >= 0'
        assert inbox_details.unread_threads >= 0, 'expected mailbox unread threads to be >= 0'

    def test_get_all_mailboxes(self, jmap_acct_1):
        # get mailbox details for all mailboxes
        results = jmap_acct_1.get_mailboxes_by_id()

        assert results, 'expected get mailbox to return mailbox details'
        assert len(results) >= len(DEFAULT_JMAP_MAILBOX_LIST), (
            f'expected at least {len(DEFAULT_JMAP_MAILBOX_LIST)} mailboxes to have been found'
        )

        # now format the list of found mailboxes to match the format in our DEFAULT_JMAP_MAILBOX_LIST
        found_mailboxes = []
        for mailbox in results:
            found_mailboxes.append(
                {
                    'id': mailbox.id,
                    'name': mailbox.name,
                    'role': mailbox.role,
                }
            )

        # now ensure that the expected default malboxes exist
        for exp_mailbox in DEFAULT_JMAP_MAILBOX_LIST:
            assert exp_mailbox in found_mailboxes, f'expected mailbox to exist with details: {exp_mailbox}'
            log.debug(f"found mailbox '{exp_mailbox['name']}'")

    def test_create_mailbox(self, jmap_acct_1):
        # create a new mailbox at root level and verify it exists
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'
        assert result['newMailbox']['id'], 'expected a mailbox id to have been returned'

        # now get mailbox by name and assert it exists
        found = jmap_acct_1.get_mailbox_by_name(name)
        assert found, 'expected new mailbox to exist'

    def test_create_one_sub_mailbox(self, jmap_acct_1):
        # create a new mailbox, then create a child mailbox/folder inside it
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'

        # now use the newly created mailbox's id as the parent id for the subfolder/mailbox
        new_parent_mailbox_id = result['newMailbox']['id']
        sub_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(mailbox_name=sub_name, parent_id=new_parent_mailbox_id)
        assert result, 'expected mailbox to have been created successfully'

        # now verify the sub mailbox exists
        child = jmap_acct_1.get_mailbox_by_name(sub_name)
        assert child, 'expected new sub-mailbox to exist'
        assert child[0].parent_id == new_parent_mailbox_id, 'expected the sub-mailbox parent id to be correct'

    def test_create_multi_sub_mailboxes(self, jmap_acct_1):
        # create a new parent mailbox, then create multiple children mailboxes/folders inside it
        # ie. one new mailbox that has 9 folders inside that one (at the same level)
        new_sub_mailboxes = []
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'

        # loop to create multiple sub-folders/mailboxes at the same level inside the one parent mailbox
        parent_mailbox_id = result['newMailbox']['id']
        for sub_count in range(9):
            sub_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
            result = jmap_acct_1.create_mailbox(mailbox_name=sub_name, parent_id=parent_mailbox_id)
            assert result, 'expected mailbox to have been created successfully'
            new_sub_mailboxes.append(sub_name)

        # now verify each sub-folder/mailbox exists
        for sub_mailbox in new_sub_mailboxes:
            found = jmap_acct_1.get_mailbox_by_name(sub_mailbox)
            assert found, 'expected new sub-mailbox to exist'
            assert found[0].parent_id == parent_mailbox_id, 'expected the sub-mailbox parent id to be correct'

    def test_create_multi_level_mailboxes(self, jmap_acct_1):
        # create a new mailbox, and then create multiple levels of sub-folders/mailboxes inside it
        new_sub_mailboxes = []
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'

        # loop to create multi levels of sub-folders/mailboxes; use the newly created mailbox's id as the parent
        # id for the next new subfolder/mailbox; 10 levels total (each mailbox will only have one sub-folder/mailbox)
        for sub_count in range(9):
            parent_mailbox_id = result['newMailbox']['id']
            sub_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
            result = jmap_acct_1.create_mailbox(mailbox_name=sub_name, parent_id=parent_mailbox_id)
            assert result, 'expected mailbox to have been created successfully'
            new_sub_mailboxes.append({'name': sub_name, 'parent_id': parent_mailbox_id})

        # now verify each sub-folder/mailbox exists
        for sub_mailbox in new_sub_mailboxes:
            found = jmap_acct_1.get_mailbox_by_name(sub_mailbox['name'])
            assert found, 'expected new sub-mailbox to exist'
            assert found[0].parent_id == sub_mailbox['parent_id'], 'expected the sub-mailbox parent id to be correct'

    def test_subscribe_mailbox(self, jmap_acct_1):
        # create a new (unsubscribed) mailbox then subscribe to it after it was created
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(mailbox_name=name, parent_id=None, is_subscribed=False)
        assert result, 'expected mailbox to have been created successfully'

        # verify new mailbox is NOT subscribed to
        mailbox_id = result['newMailbox']['id']
        mailbox_details = jmap_acct_1.get_mailboxes_by_id([mailbox_id])[0]
        assert mailbox_details.is_subscribed is False, 'expected new mailbox to not be subscribed to'

        # update mailbox and subscribe to it
        updated = jmap_acct_1.set_mailbox_subscribe_by_id(mailbox_id, True)
        assert mailbox_id in updated, 'expected the id for the renamed mailbox to be returned from the update'

        # verify new mailbox is now subscribed to
        mailbox_details = jmap_acct_1.get_mailboxes_by_id([mailbox_id])[0]
        assert mailbox_details.is_subscribed, 'expected new mailbox to be subscribed to'

    def test_unsubscribe_mailbox(self, jmap_acct_1):
        # create a new subscribed mailbox then unsubscribe to it after it was created
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(mailbox_name=name)
        assert result, 'expected mailbox to have been created successfully'

        # verify new mailbox is subscribed to
        mailbox_id = result['newMailbox']['id']
        mailbox_details = jmap_acct_1.get_mailboxes_by_id([mailbox_id])[0]
        assert mailbox_details.is_subscribed, 'expected new mailbox to be subscribed to'

        # update mailbox and unsubscribe from it
        updated = jmap_acct_1.set_mailbox_subscribe_by_id(mailbox_id, False)
        assert mailbox_id in updated, 'expected the id for the renamed mailbox to be returned from the update'

        # verify new mailbox is now subscribed to
        mailbox_details = jmap_acct_1.get_mailboxes_by_id([mailbox_id])[0]
        assert mailbox_details.is_subscribed is False, 'expected new mailbox to not be subscribed to'

    def test_rename_mailbox(self, jmap_acct_1):
        # create a new mailbox, rename it, and verify
        og_mailbox_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(og_mailbox_name)
        assert result, 'expected mailbox to have been created successfully'
        og_mailbox_id = result['newMailbox']['id']

        # rename it
        new_mailbox_name = f'{MAILBOX_PREFIX} Mailbox was RENAMED at {datetime.datetime.now()}'
        updated = jmap_acct_1.rename_mailbox_by_id(og_mailbox_id, new_mailbox_name)
        assert og_mailbox_id in updated, 'expected the id for the renamed mailbox to be returned from the update'

        # now get the details for the same mailbox by id, and verify the name was changed
        mailbox_details = jmap_acct_1.get_mailboxes_by_id([og_mailbox_id])[0]
        log.debug(f"mailbox with id '{og_mailbox_id}' now has name: {mailbox_details.name}")
        assert mailbox_details.name == new_mailbox_name, 'expected the mailbox name to have been changed'

    def test_rename_sub_mailbox(self, jmap_acct_1):
        # create a new mailbox in an existing folder/mailbox, rename it, and verify
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'

        # now use the newly created mailbox's id as the parent id for the subfolder/mailbox
        new_parent_mailbox_id = result['newMailbox']['id']
        sub_mailbox_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(mailbox_name=sub_mailbox_name, parent_id=new_parent_mailbox_id)
        assert result, 'expected mailbox to have been created successfully'

        sub_mailbox_id = new_parent_mailbox_id = result['newMailbox']['id']
        new_sub_mailbox_name = f'{MAILBOX_PREFIX} Mailbox was RENAMED at {datetime.datetime.now()}'
        updated = jmap_acct_1.rename_mailbox_by_id(sub_mailbox_id, new_sub_mailbox_name)
        assert sub_mailbox_id in updated, 'expected the id for the renamed mailbox to be returned from the update'

        # now get the details for the same mailbox by id, and verify the name was changed
        mailbox_details = jmap_acct_1.get_mailboxes_by_id([sub_mailbox_id])[0]
        log.debug(f"mailbox with id '{sub_mailbox_id}' now has name: {mailbox_details.name}")
        assert mailbox_details.name == new_sub_mailbox_name, 'expected the mailbox name to have been changed'

    def test_delete_mailbox(self, jmap_acct_1):
        # create a new mailbox, delete it, and verify
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()} to be deleted!'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'

        mailbox_id = result['newMailbox']['id']
        deleted = jmap_acct_1.delete_mailbox_by_id(mailbox_id)
        assert mailbox_id in deleted, 'expected the deleted mailbox id to be returned in the destory mailbox response'

        # now attempt to get the deleted mailbox by it's id, should not be found
        mailbox_found_id = jmap_acct_1.get_mailboxes_by_id([mailbox_id])
        assert mailbox_found_id is None, 'expected the mailbox to not have been found (by id) after deletion'

        # now attempt to get the deleted mailbox by it's name, should not be found
        mailbox_found_name = jmap_acct_1.get_mailbox_by_name(mailbox_id)
        assert mailbox_found_name is None, 'expected the mailbox to not have been found (by name) after deletion'

    def test_delete_sub_mailbox(self, jmap_acct_1):
        # create a new mailbox in an existing folder/mailbox, delete it (the sub-folder), and verify
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'

        # now use the newly created mailbox's id as the parent id for the subfolder/mailbox
        parent_mailbox_id = result['newMailbox']['id']
        sub_mailbox_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(mailbox_name=sub_mailbox_name, parent_id=parent_mailbox_id)
        assert result, 'expected mailbox to have been created successfully'

        # delete the sub-folder/mailbox
        sub_mailbox_id = result['newMailbox']['id']
        deleted = jmap_acct_1.delete_mailbox_by_id(sub_mailbox_id)
        assert sub_mailbox_id in deleted, 'expected the deleted mailbox id to be returned in the delete response'

        # now attempt to get the deleted mailbox by it's id, should not be found
        mailbox_found = jmap_acct_1.get_mailboxes_by_id([sub_mailbox_id])
        assert mailbox_found is None, 'expected the mailbox to not have been found (by id) after it was destroyed'

        # now get the parent mailbox, it should still exist
        mailbox_found = jmap_acct_1.get_mailboxes_by_id([parent_mailbox_id])
        assert mailbox_found, 'expected the parent mailbox to still exist after the sub-folder was destroyed'

    def test_delete_mailbox_containing_child(self, jmap_acct_1):
        # create a new mailbox, then create a child mailbox/folder inside it; then attempt to delete the top-level
        # mailbox (should fail because top-level mailbox was created with )
        name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(name)
        assert result, 'expected mailbox to have been created successfully'

        # now use the newly created mailbox's id as the parent id for the subfolder/mailbox
        parent_mailbox_id = result['newMailbox']['id']
        sub_mailbox_name = f'{MAILBOX_PREFIX} {datetime.datetime.now()}'
        result = jmap_acct_1.create_mailbox(mailbox_name=sub_mailbox_name, parent_id=parent_mailbox_id)
        assert result, 'expected mailbox to have been created successfully'

        # attempt to delete the top-level parent mailbox, verify error
        result = jmap_acct_1.delete_mailbox_by_id(parent_mailbox_id)
        assert parent_mailbox_id in result['methodResponses'][0][1]['notDestroyed'], (
            'expected the parent mailbox id to be returned as notDestroyed'
        )
        assert (
            result['methodResponses'][0][1]['notDestroyed'][parent_mailbox_id]['description']
            == JMAP_DELETE_MAILBOX_WITH_CHILD_ERR
        ), 'expected the correct mailbox destroy error'

        # verify parent mailbox still exists
        mailbox_found = jmap_acct_1.get_mailboxes_by_id([parent_mailbox_id])
        assert mailbox_found, 'expected the parent mailbox to still exist'
