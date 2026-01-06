import caldav
import gevent

from common.logger import log

from common.const import (
    TASK_STATUS_COMPLETED,
)

from locust import events


class CalDAV:
    def __init__(self, caldav_server_url, timeout, locust=False):
        self.caldav_server_url = caldav_server_url
        self.connection_timeout = timeout
        self.client = None
        self.principal = None
        self.locust = locust

    def login(self, username, password):
        """
        Connect and sign in to the caldav server as defined in the .env.test file.
        """
        self.username = username
        success = False

        # create a caldav client
        self.client = caldav.DAVClient(
            url=f'{self.caldav_server_url}/{username}',
            headers={
                'Authorization': 'Basic',
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
            auth=(username, password),
            timeout=self.connection_timeout,  # give extra time as requests takes longer in CI
        )

        # now sign in and get our principal object
        try:
            log.debug(f"connecting to caldav at '{self.caldav_server_url}' with username '{username.split('@')[0]}'")
            self.principal = self.client.principal()
            log.debug('successfully connected to caldav server')
            success = True

        except Exception as e:
            log.debug(f'failed to connect to caldav server: {e}')

        return success

    def logout(self):
        log.debug(f'closing caldav client session {self.username.split("@")[0]}')

        try:
            self.client.close()  # is no return value
        except Exception as e:
            log.debug(f'{str(e)}')

    def get_calendars(self):
        """
        Retrieve and return all of the calendars that exist for our current signed-in caldav principal.
        """
        log.debug('retrieving calendars')
        cals_found = self.principal.calendars()
        log.debug(f'found {len(cals_found)} calendar(s)')

        return cals_found

    def get_default_calendar(self):
        """
        Retrieve and return the default calendar for our current signed-in caldav principal.
        """
        all_cals = self.get_calendars()
        assert len(all_cals) > 0, 'expected default calendar to exist'

        for next_cal in all_cals:
            if next_cal.id == 'default':
                log.debug('found default calendar')
                return next_cal

        log.debug('default calendar was not found')
        return None

    def make_calendar(self, cal_name):
        """
        Create a new calendar with the given name using the current principal user.
        """
        log.debug(f'creating new calendar with name: {cal_name}')

        try:
            new_calendar = self.principal.make_calendar(cal_name)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert new_calendar, 'expected to be able to create a new calendar'
        assert new_calendar.id, 'expected new calendar to have an id'
        log.debug(f'calendar successfully created with id: {new_calendar.id}')

        return new_calendar

    def does_calendar_exist_by_id(self, cal_id):
        """
        Check if the given calendar id matches any currently existing calendar.
        """
        all_cals = self.get_calendars()

        for next_cal in all_cals:
            if next_cal.id == cal_id:
                log.debug(f'found calendar with id: {cal_id}')
                return True

        log.debug(f"calendar with id '{cal_id}' does not exist")
        return False

    def delete_calendar(self, calendar):
        """
        Delete the given calendar.
        """
        log.debug(f'deleting calendar "{calendar.name}" (id: {calendar.id})')

        try:
            calendar.delete()

        except Exception:
            log.debug('error deleting calendar: {e}')
            return False

        log.debug(f"calendar with id: '{calendar.id}' successfully deleted")
        return True

    def cleanup_test_calendars(self, calendar_prefix):
        """
        Find all existing caldav calendars with a name that match the given prefix and delete them.
        """
        existing_cals = self.get_calendars()

        for cal in existing_cals:
            if calendar_prefix in cal.name:
                try:
                    self.delete_calendar(cal)
                except Exception as _ex:
                    # we don't really care if it failed for some reason as just cleaning up
                    pass

    def get_calendar_by_name(self, cal_name_to_find):
        """
        Get and return the calendar that has the given name (or None if it doesn't exist).
        """
        log.debug(f'looking for calendar with name: {cal_name_to_find}')

        try:
            cal = self.principal.calendar(name=cal_name_to_find)

        except Exception as e:
            log.debug(f'error finding calendar: {e}')
            return None

        log.debug('calendar found')
        return cal

    def create_event(self, test_cal, event_props):
        """
        Add the given event to the given calendar.
        """
        new_event = None
        add_event_exception = None
        log.debug(f'adding event to calendar "{test_cal.name}": {event_props}')

        if self.locust:
            # locust uses gevent greenlets to run concurrent users in single process
            start_time = gevent.get_hub().loop.now()

        try:
            new_event = test_cal.save_event(
                dtstart=event_props['dtstart'],
                dtend=event_props['dtend'],
                summary=event_props.get('summary', 'new test event'),
            )
        except Exception as e:
            add_event_exception = str(e)
            log.debug(f'caught exception: {str(e)}')

        # if running a locust load test we need to let locust know the create event is done
        if self.locust:
            events.request.fire(
                request_type='caldav',
                name='create_event',
                response_time=(gevent.get_hub().loop.now() - start_time) * 1000,  # convert to ms
                response_length=len(new_event.id),
                context=None,
                exception=add_event_exception,
            )
        else:
            assert new_event, 'expected to be able to create a new event'
            assert new_event.id, 'expected new event to have an id'

        log.debug(f'calendar event successfully created with id: {new_event.id}')

        return new_event

    def delete_event(self, event_to_delete):
        """
        Delete the given calendar event.
        """
        log.debug(f'deleting calendar event "{event_to_delete.component["summary"]}" (id: {event_to_delete.id})')

        try:
            event_to_delete.delete()

        except Exception:
            log.debug('error deleting calendar event: {e}')
            return False

        log.debug(f"calendar event with id: '{event_to_delete.id}' successfully deleted")
        return True

    def get_all_events(self, test_cal):
        """
        Get all of the existing events in the given calendar.
        """
        log.debug(f'getting all events from calendar "{test_cal.name}"')

        try:
            found_events = test_cal.events()
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found_events)} existing event(s)')

        return found_events

    def get_events_by_summary(self, test_cal, event_summary):
        """
        Search the given calendar for any events that have the given event summary.
        """
        log.debug(f'searching calendar "{test_cal.name}" for events with summary "{event_summary}"')

        try:
            found_events = test_cal.search(event=True, summary=event_summary)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found_events)} matching event(s)')

        return found_events

    def get_event_by_uid(self, test_cal, event_uid):
        """
        Search the given calendar for an event with the given uid.
        """
        log.debug(f'searching calendar "{test_cal.name}" for event with id {event_uid}')

        try:
            found = test_cal.search(event=True, uid=event_uid)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found)} matching event(s)')

        return found[0] if len(found) else None

    def get_events_by_datetime(self, test_cal, dtstart, dtend):
        """
        Search the given calendar for any events between the dtstart and dtend datetimes.
        """
        log.debug(f'searching calendar "{test_cal.name}" for events from {dtstart} to {dtend}')

        try:
            found_events = test_cal.search(
                event=True,
                start=dtstart,
                end=dtend,
            )
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found_events)} matching event(s)')

        return found_events

    def create_task(self, test_cal, task_props):
        """
        Add the given task to the given calendar.
        """
        log.debug(f'adding task to calendar "{test_cal.name}": {task_props}')

        try:
            new_task = test_cal.save_todo(
                summary=task_props.get('summary', 'new test task'),
                description=task_props.get('description'),
                priority=task_props.get('priority'),
                categories=task_props.get('categories'),
                dtstart=task_props.get('dtstart'),
                due=task_props.get('due'),
            )
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert new_task, 'expected to be able to create a new task'
        assert new_task.id, 'expected new task to have an id'
        log.debug(f'task successfully created with id: {new_task.id}')

        return new_task

    def get_tasks_by_summary(self, test_cal, task_summary):
        """
        Search the given calendar for any tasks that have the given summary.
        """
        log.debug(f'searching calendar "{test_cal.name}" for tasks with summary "{task_summary}"')

        try:
            found_tasks = test_cal.search(todo=True, summary=task_summary)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found_tasks)} matching task(s)')

        return found_tasks

    def get_task_by_uid(self, test_cal, event_uid):
        """
        Search the given calendar for a task with the given uid. Will return the task even if it is marked
        as completed.
        """
        log.debug(f'searching calendar "{test_cal.name}" for task with id {event_uid}')

        try:
            found = test_cal.search(todo=True, uid=event_uid, include_completed=True)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found)} matching task(s)')

        return found[0] if len(found) else None

    def get_tasks_by_category(self, test_cal, task_category):
        """
        Search the given calendar for tasks with the given category.
        """
        log.debug(f'searching calendar "{test_cal.name}" for tasks with category {task_category}')

        try:
            found = test_cal.search(todo=True, category=task_category, include_completed=True)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found)} matching task(s)')

        return found if len(found) else None

    def get_completed_tasks(self, test_cal):
        """
        Return tasks from the given calendar that have a status of completed.
        """
        log.debug(f'searching calendar "{test_cal.name}" for completed tasks')

        try:
            found = test_cal.search(todo=True, status=TASK_STATUS_COMPLETED, include_completed=True)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found)} completed task(s)')

        return found if len(found) else None

    def get_all_tasks(self, test_cal):
        """
        Get all of the existing tasks in the given calendar, including completed ones.
        """
        log.debug(f'getting all tasks from calendar "{test_cal.name}"')

        try:
            found_tasks = test_cal.todos(include_completed=True)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        log.debug(f'found {len(found_tasks)} existing tasks')

        return found_tasks
