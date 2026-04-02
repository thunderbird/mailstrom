import pytest
import pytz
import time

from datetime import datetime, timedelta

from common.CalDAV import CalDAV
from common.logger import log

from common.const import (
    EVENT_PREFIX,
    TEST_SLEEP_1_SECOND,
)

from const import (
    TEST_CALDAV_URL,
    CONNECT_TIMEOUT,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


class TestCaldavEvents:
    # build a list of events that we want to test creating, by providing the dtstart and dtend of each event to create
    test_events = []
    tz_utc = pytz.timezone('UTC')  # we use UTC so there's no daylight savings time interference
    tomorrow = datetime.now(tz=tz_utc) + timedelta(days=1)

    # tomorrow 9am for 15 minutes
    start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(minutes=15))))

    # tomorrow 11am to 1pm
    start = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=2))))

    # an appointment that overlaps an existing one (tomorrow moon to 2pm)
    start = tomorrow.replace(hour=12, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=2))))

    # tomorrow 3pm - 4pm
    start = tomorrow.replace(hour=15, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=1))))

    # a second appointment at the same time as an existing one (tomorrow 3pm - 4pm)
    test_events.append(test_events[3])

    # a zero duration appointment (tomorrow 6pm)
    start = tomorrow.replace(hour=18, minute=0, second=0, microsecond=0)
    test_events.append((start, start))

    # a one minute appointment tomorrow 7:00pm to 7:01pm
    start = tomorrow.replace(hour=19, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(minutes=1))))

    # spans midnight (tomorrow 11:30pm to 12:30am the next day)
    start = tomorrow.replace(hour=23, minute=30, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=1))))

    # two days from now 9am - 5pm
    two_days_from_now = datetime.now(tz=tz_utc) + timedelta(days=2)
    start = two_days_from_now.replace(hour=9, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=8))))

    # one week from now at 9am with a duration of 3 days
    one_week_from_now = datetime.now(tz=tz_utc) + timedelta(days=7)
    start = one_week_from_now.replace(hour=9, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(days=3))))

    # one month from now
    one_month_from_now = datetime.now(tz=tz_utc) + timedelta(days=30)
    start = one_month_from_now.replace(hour=7, minute=30, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=3))))

    # one year from now for an entire week
    one_year_from_now = datetime.now(tz=tz_utc) + timedelta(days=365)
    start = one_year_from_now.replace(hour=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(days=7))))

    # yesterday at 1pm for 30 minutes
    yesterday = datetime.now(tz=tz_utc) + timedelta(days=-1)
    start = yesterday.replace(hour=13, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(minutes=30))))

    # one week ago at 5pm for 90 minutes
    one_week_ago = datetime.now(tz=tz_utc) + timedelta(days=-7)
    start = one_week_ago.replace(hour=17, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(minutes=90))))

    # one month ago 9am to 11am
    one_month_ago = datetime.now(tz=tz_utc) + timedelta(days=-30)
    start = one_month_ago.replace(hour=9, minute=0, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=2))))

    # one year ago at 7pm for 3 hours
    one_year_ago = datetime.now(tz=tz_utc) + timedelta(days=-365)
    start = one_year_ago.replace(hour=19, second=0, microsecond=0)
    test_events.append((start, (start + timedelta(hours=3))))

    @pytest.mark.parametrize('event_start, event_end', test_events)
    def test_create_event(self, caldav, test_calendar, event_start, event_end):
        # create an event in the test calendar with the given start and end datetimes and verify (the test
        # calendar is automatically created before the tests run (via the test_calendar fixture in conftest.py)
        event_props = {
            'dtstart': event_start,
            'dtend': event_end,
            'summary': f'{EVENT_PREFIX} created at {datetime.now()}',
        }
        created_event = caldav.create_event(test_calendar, event_props)

        # now search for our event to verify it was created
        time.sleep(TEST_SLEEP_1_SECOND)
        found_events = caldav.get_events_by_summary(test_calendar, event_props['summary'])
        assert len(found_events) == 1
        found_event = found_events[0]

        assert found_event.parent.id == test_calendar.id, 'expected event parent calendar id to be correct'
        assert TEST_CALDAV_URL in str(found_event.url), 'expected event url to contain the caldav host'
        assert created_event.id in str(found_event.url), 'expected event url to contain the event id'

        # the event .component is used to access the event as an iCalendar object
        assert found_event.component.get('summary') == event_props['summary'], 'expected event summary to be correct'
        assert found_event.component.get('uid') == created_event.id, 'expected event uid to be correct'

        # .dt converts event ical object dtstart to python datetime obj
        assert found_event.component.get('dtstart').dt == event_props['dtstart'], (
            'expected event start datetime to be correct'
        )
        assert found_event.component.get('dtend').dt == event_props['dtend'], 'expected event end time to be correct'

    @pytest.mark.sanity
    def test_create_and_edit_event(self, caldav, test_calendar):
        # create an event in the test calendar then modify the event, verify
        # let's create an event that starts at 9am two days from now, and has a duration of 1 hour
        two_days_from_now = datetime.now(tz=self.tz_utc) + timedelta(days=2)
        two_days_from_now_9am = two_days_from_now.replace(hour=9, minute=0, second=0, microsecond=0)
        event_end = two_days_from_now_9am + timedelta(hours=1)

        event_props = {
            'dtstart': two_days_from_now_9am,
            'dtend': event_end,
            'summary': f'{EVENT_PREFIX} created at {datetime.now()}',
        }
        test_event = caldav.create_event(test_calendar, event_props)

        # verify the new event exists (search by event id)
        time.sleep(TEST_SLEEP_1_SECOND)
        found_event = caldav.get_event_by_uid(test_calendar, test_event.id)
        assert found_event, 'expected new event to exist'

        # modify the event and verify
        new_summary = f'{event_props["summary"]} modified!'
        new_dtstart = two_days_from_now_9am + timedelta(hours=2)  # change to start 11am
        new_dtend = new_dtstart + timedelta(hours=1)  # change to end at noon
        found_event.component['summary'] = new_summary
        found_event.component['dtstart'].dt = new_dtstart
        found_event.component['dtend'].dt = new_dtend
        log.debug(f'saving modified event (id {test_event.id})')
        found_event.save()

        # search for the same event again by id and verify it was modified
        time.sleep(TEST_SLEEP_1_SECOND)
        updated_event = caldav.get_event_by_uid(test_calendar, found_event.id)
        assert updated_event, 'expected modified event to exist'
        assert updated_event.component.get('summary') == new_summary, 'expected event summary to have been modified'
        assert updated_event.component.get('dtstart').dt == new_dtstart, (
            'expected event start datetime to have been modified'
        )
        assert updated_event.component.get('dtend').dt == new_dtend, 'expected event end datetime to have been modified'

    def test_delete_event(self, caldav, test_calendar):
        # create a calendar event then delete it and verify
        tomorrow_9pm = self.tomorrow.replace(hour=21, minute=0, second=0, microsecond=0)

        event_props = {
            'dtstart': tomorrow_9pm,
            'dtend': tomorrow_9pm + timedelta(minutes=30),
            'summary': f'{EVENT_PREFIX} delete test (created at {datetime.now()})',
        }

        test_event = caldav.create_event(test_calendar, event_props)

        # verify we can see the new event
        time.sleep(TEST_SLEEP_1_SECOND)
        found_event = caldav.get_event_by_uid(test_calendar, test_event.id)
        assert found_event, 'expected new event to exist'

        # delete it
        result = caldav.delete_event(test_event)
        assert result, 'expected to be able to delete the event'

        # verify no longer exists
        time.sleep(TEST_SLEEP_1_SECOND)
        found_event = caldav.get_event_by_uid(test_calendar, test_event.id)
        assert not found_event, 'expected event to not have been found after it was deleted'

    @pytest.mark.sanity
    def test_get_all_events(self, caldav, test_calendar):
        # get all events from the test calendar (we know there is at least one event in the test calendar because
        # an event is added when the test calendar is created (via the test_calendar fixture in conftest.py)
        events = caldav.get_all_events(test_calendar)
        assert len(events) >= 1, 'expected at least one event to exist in the test calendar'

        for event in events:
            # each event parent id should be our test calendar id, and our event prefix in the summary
            log.debug(
                f'event {event.component.get("uid")}: "{event.component["summary"]}" {event.component["dtstart"].dt}'
                + f' to {event.component.get("dtend").dt}'
            )
            assert event.parent.id == test_calendar.id, 'expected event parent calendar id to be correct'
            assert EVENT_PREFIX in event.component.get('summary'), 'expected event summary to be correct'

    def test_get_events_by_date(self, caldav, test_calendar):
        # create multiple events on specific days in our test calendar, then search for them by date
        # use days that we know other tests haven't added events on so we will know how many to expect
        events_four_days_from_now_start = []
        four_days_from_now = datetime.now(tz=self.tz_utc) + timedelta(days=4)
        events_four_days_from_now_start.append(four_days_from_now.replace(hour=9, minute=0, second=0, microsecond=0))
        events_four_days_from_now_start.append(four_days_from_now.replace(hour=10, minute=30, second=0, microsecond=0))
        events_four_days_from_now_start.append(four_days_from_now.replace(hour=14, minute=0, second=0, microsecond=0))
        events_four_days_from_now_start.append(four_days_from_now.replace(hour=17, minute=0, second=0, microsecond=0))

        events_five_days_from_now_start = []
        five_days_from_now = datetime.now(tz=self.tz_utc) + timedelta(days=5)
        events_five_days_from_now_start.append(five_days_from_now.replace(hour=8, minute=0, second=0, microsecond=0))
        events_five_days_from_now_start.append(five_days_from_now.replace(hour=11, minute=30, second=0, microsecond=0))
        events_five_days_from_now_start.append(five_days_from_now.replace(hour=15, minute=0, second=0, microsecond=0))

        all_events_start = events_four_days_from_now_start.copy() + events_five_days_from_now_start.copy()

        # create all the events (one hour duration each one is fine)
        for next_start in all_events_start:
            event_props = {
                'dtstart': next_start,
                'dtend': next_start + timedelta(hours=1),
                'summary': f'{EVENT_PREFIX} search test (created at {datetime.now()})',
            }
            caldav.create_event(test_calendar, event_props)

        # search for events between 6am and 7am on the day four days from now (expect none)
        time.sleep(TEST_SLEEP_1_SECOND)
        search_start = four_days_from_now.replace(hour=6, minute=0, second=0, microsecond=0)
        found = caldav.get_events_by_datetime(test_calendar, search_start, (search_start + timedelta(hours=1)))
        assert len(found) == 0, 'expected no events to have been found'

        # search for events at any time during the day four days from now (expect 4)
        search_start = four_days_from_now.replace(hour=0, minute=0, second=0, microsecond=0)
        found = caldav.get_events_by_datetime(test_calendar, search_start, (search_start + timedelta(hours=24)))
        exp_count = len(events_four_days_from_now_start)
        assert len(found) == exp_count, f'expected {exp_count} events to have been found'

        # search for events during 7am and 11am four days from now (expect 2 events)
        search_start = four_days_from_now.replace(hour=7, minute=0, second=0, microsecond=0)
        found = caldav.get_events_by_datetime(test_calendar, search_start, (search_start + timedelta(hours=4)))
        assert len(found) == 2, 'expected 2 events to have been found'

        # search for events at any time during the day five days from now (expect 3)
        search_start = five_days_from_now.replace(hour=0, minute=0, second=0, microsecond=0)
        found = caldav.get_events_by_datetime(test_calendar, search_start, (search_start + timedelta(hours=24)))
        exp_count = len(events_five_days_from_now_start)
        assert len(found) == exp_count, f'expected {exp_count} events to have been found'

        # search for events from 8am four days from now until 6pm five days from now (expect all)
        search_start = four_days_from_now.replace(hour=8, minute=0, second=0, microsecond=0)
        search_end = five_days_from_now.replace(hour=18, minute=0, second=0, microsecond=0)
        found = caldav.get_events_by_datetime(test_calendar, search_start, search_end)
        exp_count = len(all_events_start)
        assert len(found) == exp_count, f'expected {exp_count} events to have been found'

    def test_event_visible_multiple_clients(self, caldav, test_calendar):
        # add event with one client, verify the event is sync'd/seen with 2nd client
        # our first caldav client is the one provided by the fixture; we'll create a second one
        second_caldav_client = CalDAV(TEST_CALDAV_URL, CONNECT_TIMEOUT)
        login_success = second_caldav_client.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert login_success, 'expected to be able to connect to caldav server'

        # create a test event in our test calendar with our first caldav client
        tomorrow_8pm = self.tomorrow.replace(hour=20, minute=0, second=0, microsecond=0)

        event_props = {
            'dtstart': tomorrow_8pm,
            'dtend': tomorrow_8pm + timedelta(hours=1),
            'summary': f'{EVENT_PREFIX} created at {datetime.now()}',
        }

        test_event = caldav.create_event(test_calendar, event_props)

        # now search for event with the second caldav client and ensure it is found
        time.sleep(TEST_SLEEP_1_SECOND)
        found = second_caldav_client.get_event_by_uid(test_calendar, test_event.id)
        assert found, 'expected event to have been found by second caldav client'

        # delete the event with the second caldav client
        result = second_caldav_client.delete_event(test_event)
        assert result, 'expected to be able to delete the event using second caldav client'

        # now search for the event with the first caldav client and it shouldn't be found
        time.sleep(TEST_SLEEP_1_SECOND)
        found = caldav.get_event_by_uid(test_calendar, test_event.id)
        assert not found, (
            'expected the event to not be found by first caldav client after it was deleted by the second client'
        )

        # done with our second client
        second_caldav_client.logout()
