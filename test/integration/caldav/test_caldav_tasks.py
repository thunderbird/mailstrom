import pytest
import pytz
import time

from datetime import datetime, timedelta

from common.CalDAV import CalDAV
from common.logger import log

from common.const import (
    TASK_PREFIX,
    TASK_STATUS_NEEDS_ACTION,
    TASK_STATUS_COMPLETED,
    TASK_PRIORITY_HIGH,
    TASK_PRIORITY_MEDIUM,
    TASK_CATEGORY_FAVOURITES,
    TASK_CATEGORY_BUSINESS,
    TASK_CATEGORY_VACATION,
    TEST_SLEEP_1_SECOND,
)

from const import (
    TEST_CALDAV_URL,
    CONNECT_TIMEOUT,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


class TestCaldavTasks:
    tz_utc = pytz.timezone('UTC')  # use UTC so there's no daylight savings time interference
    now = datetime.now(tz=tz_utc).replace(second=0, microsecond=0)

    @pytest.mark.sanity
    def test_create_task(self, caldav, test_calendar):
        # create a task in the test calendar and verify (the test calendar is automatically
        # created before the tests run (via the test_calendar fixture in conftest.py)
        one_week_from_now = self.now + timedelta(days=7)

        task_props = {
            'summary': f'{TASK_PREFIX} created at {datetime.now()}',
            'description': 'This is a task created by the mailstrom integration tests.',
            'priority': TASK_PRIORITY_HIGH,
            'categories': TASK_CATEGORY_FAVOURITES,
            'dtstart': self.now,
            'due': one_week_from_now,
        }
        created_task = caldav.create_task(test_calendar, task_props)

        # now search for our task to verify it was created
        time.sleep(TEST_SLEEP_1_SECOND)
        found_tasks = caldav.get_tasks_by_summary(test_calendar, task_props['summary'])
        assert len(found_tasks) == 1
        found_task = found_tasks[0]
        found_task_category = found_task.component.get('categories').to_ical().decode()

        assert found_task.parent.id == test_calendar.id, 'expected task parent calendar id to be correct'
        assert TEST_CALDAV_URL in str(found_task.url), 'expected task url to contain the caldav host'
        assert created_task.id in str(found_task.url), 'expected event url to contain the task id'

        # the event .component is used to access the event as an iCalendar object
        assert found_task.component.get('summary') == task_props['summary'], 'expected task summary to be correct'
        assert found_task.component.get('description') == task_props['description'], 'expected correct task desc'
        assert found_task.component.get('uid') == created_task.id, 'expected task uid to be correct'
        assert found_task.component.get('status') == TASK_STATUS_NEEDS_ACTION, 'expected task status to be correct'
        assert found_task.component.get('priority') == TASK_PRIORITY_HIGH, 'expected task priority to be correct'
        assert found_task.component.get('dtstart').dt == self.now, 'expected task due date to be correct'
        assert found_task.component.get('due').dt == one_week_from_now, 'expected task due date to be correct'
        assert found_task_category == TASK_CATEGORY_FAVOURITES, 'expected task category to be correct'

    def test_edit_task(self, caldav, test_calendar):
        # create a task in the test calendar then modify it and verify
        one_day_from_now = self.now + timedelta(days=1)

        task_props = {
            'summary': f'{TASK_PREFIX} created at {datetime.now()}',
            'description': 'This is a task created by the mailstrom integration tests.',
            'priority': TASK_PRIORITY_MEDIUM,
            'categories': TASK_CATEGORY_FAVOURITES,
            'dtstart': self.now,
            'due': one_day_from_now,
        }
        test_task = caldav.create_task(test_calendar, task_props)

        # verify the new task exists (search by event id)
        time.sleep(TEST_SLEEP_1_SECOND)
        found_task = caldav.get_task_by_uid(test_calendar, test_task.id)
        assert found_task, 'expected new task to exist'

        # modify the task and verify
        new_summary = f'{task_props["summary"]} modified!'
        new_dtstart = one_day_from_now + timedelta(days=1)
        new_due = new_dtstart + timedelta(days=7)
        new_desc = f'{task_props["description"]} modified!'
        found_task.component['summary'] = new_summary
        found_task.component['dtstart'].dt = new_dtstart
        found_task.component['due'].dt = new_due
        found_task.component['description'] = new_desc
        log.debug(f'saving modified task (id {test_task.id})')
        found_task.save()

        # search for the same task again by id and verify it was modified
        time.sleep(TEST_SLEEP_1_SECOND)
        updated_task = caldav.get_task_by_uid(test_calendar, test_task.id)

        assert updated_task, 'expected task to exist'
        assert updated_task.component.get('summary') == new_summary, 'expected task summary to have been modified'
        assert updated_task.component.get('dtstart').dt == new_dtstart, (
            'expected task start datetime to have been modified'
        )
        assert updated_task.component.get('due').dt == new_due, 'expected task due datetime to have been modified'
        assert updated_task.component.get('description') == new_desc, 'expected new task desc'

    @pytest.mark.sanity
    def test_mark_task_completed(self, caldav, test_calendar):
        # create a task and mark it completed, verify
        one_day_from_now = self.now + timedelta(days=1)

        task_props = {
            'summary': f'{TASK_PREFIX} created at {datetime.now()}',
            'description': 'This is a task created by the mailstrom integration tests.',
            'priority': TASK_PRIORITY_MEDIUM,
            'categories': TASK_CATEGORY_FAVOURITES,
            'dtstart': self.now,
            'due': one_day_from_now,
        }
        test_task = caldav.create_task(test_calendar, task_props)

        # verify the new task exists (search by event id)
        time.sleep(TEST_SLEEP_1_SECOND)
        found_task = caldav.get_task_by_uid(test_calendar, test_task.id)
        assert found_task, 'expected new task to exist'

        # set the task as completed
        log.debug(f'marking task as complete (id {test_task.id})')
        found_task.complete()

        # search for the same task again by id and verify it is now marked as complete
        time.sleep(TEST_SLEEP_1_SECOND)
        updated_task = caldav.get_task_by_uid(test_calendar, test_task.id)

        assert updated_task, 'expected task to exist'
        assert updated_task.component.get('status') == TASK_STATUS_COMPLETED, (
            'expected task to have been marked complete'
        )

    def test_delete_task(self, caldav, test_calendar):
        # create a task and then delete it and verify
        one_day_from_now = self.now + timedelta(days=1)

        task_props = {
            'summary': f'{TASK_PREFIX} created at {datetime.now()}',
            'description': 'Yet another task created by the mailstrom integration tests.',
            'priority': TASK_PRIORITY_MEDIUM,
            'categories': TASK_CATEGORY_FAVOURITES,
            'dtstart': self.now,
            'due': one_day_from_now,
        }
        test_task = caldav.create_task(test_calendar, task_props)

        # verify the new task exists (search by event id)
        time.sleep(TEST_SLEEP_1_SECOND)
        found_task = caldav.get_task_by_uid(test_calendar, test_task.id)
        assert found_task, 'expected new task to exist'

        # delete the task
        log.debug(f'deleting task (id {test_task.id})')
        found_task.delete()

        # search for the same task again but this time it won't be found
        time.sleep(TEST_SLEEP_1_SECOND)
        deleted_task = caldav.get_task_by_uid(test_calendar, test_task.id)

        assert deleted_task is None, 'expected deleted task to no longer exist'

    def test_get_tasks_by_category(self, caldav, test_calendar):
        # get tasks by category; create three new tasks, two in one category and one in another
        task_props = {
            'summary': f'{TASK_PREFIX} created at {datetime.now()}',
            'description': 'Hello from the mailstrom integration tests.',
            'priority': TASK_PRIORITY_MEDIUM,
            'categories': TASK_CATEGORY_BUSINESS,
        }

        # create two tasks in business category
        first_task = caldav.create_task(test_calendar, task_props)
        second_task = caldav.create_task(test_calendar, task_props)

        # create third task in vacation category
        task_props['categories'] = TASK_CATEGORY_VACATION
        third_task = caldav.create_task(test_calendar, task_props)

        # now get tasks that belong in one category only and verify
        found_tasks = caldav.get_tasks_by_category(test_calendar, TASK_CATEGORY_BUSINESS)
        assert len(found_tasks) >= 2, 'expected at least two tasks to be found in the search category'

        found_tasks_ids = [task.component['uid'] for task in found_tasks]

        assert first_task.id in found_tasks_ids, 'expected the first task to be found in the category search'
        assert second_task.id in found_tasks_ids, 'expected the second task to be found in the category search'
        assert third_task.id not in found_tasks_ids, 'expected the third task not to be found in the category search'

    def test_get_completed_tasks(self, caldav, test_calendar):
        # create two new tasks, mark one as completed; then get completed tasks and verify
        task_props = {
            'summary': f'{TASK_PREFIX} created at {datetime.now()}',
            'description': 'Written by the mailstrom integration tests.',
            'priority': TASK_PRIORITY_MEDIUM,
            'categories': TASK_CATEGORY_BUSINESS,
        }

        # create two new tasks (in progress by default)
        first_task = caldav.create_task(test_calendar, task_props)
        second_task = caldav.create_task(test_calendar, task_props)

        # mark first task as completed
        log.debug(f'marking task as completed (id {first_task.id})')
        first_task.complete()

        # now search for completed tasks and verify
        completed_tasks = caldav.get_completed_tasks(test_calendar)
        assert len(completed_tasks) >= 1, 'expected at least one completed tasks to have been found'

        completed_tasks_ids = [task.component['uid'] for task in completed_tasks]

        assert first_task.id in completed_tasks_ids, 'expected the first task to be found in completed tasks list'
        assert second_task.id not in completed_tasks_ids, 'expected the second task not to be found in completed tasks'

    @pytest.mark.sanity
    def test_get_all_tasks(self, caldav, test_calendar):
        # retrieve all existing tasks; we know that at least one task already exists because one is created
        # in our test calendar automatically at the test suite start (see test_calendar in conftest.py)
        all_tasks = caldav.get_all_tasks(test_calendar)
        assert len(all_tasks) > 0, 'epected at least one task to be found'

        for task in all_tasks:
            # each task parent id should be our test calendar id, and our task prefix in the summary
            log.debug(
                f'task {task.component.get("uid")}: "{task.component["summary"]}" status: {task.component["status"]}'
            )
            assert task.parent.id == test_calendar.id, 'expected task parent calendar id to be correct'
            assert TASK_PREFIX in task.component.get('summary'), 'expected task summary to be correct'

    def test_task_visible_multiple_clients(self, caldav, test_calendar):
        # add task with one client, verify the task is sync'd/seen with 2nd client
        # our first caldav client is the one provided by the fixture; we'll create a second one
        second_caldav_client = CalDAV(TEST_CALDAV_URL, CONNECT_TIMEOUT)
        login_success = second_caldav_client.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert login_success, 'expected to be able to connect to caldav server'

        # create a task using the first client
        task_props = {
            'summary': f'{TASK_PREFIX} created at {datetime.now()}',
            'description': 'Created by the first CalDAV test client.',
            'priority': TASK_PRIORITY_MEDIUM,
            'categories': TASK_CATEGORY_FAVOURITES,
        }

        test_task = caldav.create_task(test_calendar, task_props)

        # verify the new task is now seen by both of the caldav clients
        time.sleep(TEST_SLEEP_1_SECOND)
        found_task = caldav.get_task_by_uid(test_calendar, test_task.id)
        assert found_task, 'expected first caldav client to see the new task'
        found_task = second_caldav_client.get_task_by_uid(test_calendar, test_task.id)
        assert found_task, 'expected second caldav client to see the new task'

        # delete the task
        log.debug(f'deleting task (id {test_task.id})')
        found_task.delete()

        # now both caldav clients shouldn't see the task anymore
        time.sleep(TEST_SLEEP_1_SECOND)
        found_task = caldav.get_task_by_uid(test_calendar, test_task.id)
        assert found_task is None, 'expected first caldav client to no longer see the task'
        found_task = second_caldav_client.get_task_by_uid(test_calendar, test_task.id)
        assert found_task is None, 'expected second caldav client to no longer see the task'
