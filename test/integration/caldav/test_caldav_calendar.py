import pytest
import time

from datetime import datetime
from urllib.parse import quote

from common.CalDAV import CalDAV

from common.const import (
    CALENDAR_PREFIX,
    TEST_SLEEP_1_SECOND,
)

from const import (
    CONNECT_TIMEOUT,
    CALDAV_EXP_DEFAULT_CALENDAR_NAME,
    TEST_CALDAV_URL,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_PASSWORD,
)


class TestCaldavCalendar:
    def test_get_calendars(self, caldav):
        # get all of the calendars, should be at least one
        cals_returned = caldav.get_calendars()
        assert len(cals_returned) > 0, 'expected at least 1 calendar to have been returned'

    @pytest.mark.sanity
    def test_get_default_calendar(self, caldav):
        # retrieve the default calendar and verify
        default_cal = caldav.get_default_calendar()

        assert default_cal, 'expected default calendar to exist'
        exp_url = f'{caldav.caldav_server_url}/{quote(caldav.username)}/default/'
        assert default_cal.url == exp_url, 'expected default calendar url to be correct'

        display_name = default_cal.get_display_name()
        assert CALDAV_EXP_DEFAULT_CALENDAR_NAME in display_name, 'expected the default calendar name to be correct'

    @pytest.mark.sanity
    def test_create_calendar(self, caldav):
        # create a new calendar and verify
        cal_name = f'{CALENDAR_PREFIX} {datetime.now()}'
        new_calendar = caldav.make_calendar(cal_name)

        assert new_calendar.name == cal_name, 'expected new calendar name to be correct'
        exp_url = f'{caldav.caldav_server_url}/{quote(caldav.username)}/{new_calendar.id}/'
        assert new_calendar.url == exp_url, 'expected new calendar url to be correct'

        # now get all calendars and verify new one actually exists
        assert caldav.does_calendar_exist_by_id(new_calendar.id), 'expected get calendars to find the new calendar'

    def test_get_calendar_by_name(self, caldav):
        # create a new calendar then get it using the name
        cal_name = f'{CALENDAR_PREFIX} {datetime.now()}'
        caldav.make_calendar(cal_name)

        time.sleep(TEST_SLEEP_1_SECOND)
        cal_found = caldav.get_calendar_by_name(cal_name)
        assert cal_found, 'expected to be able to find calendar by name'
        assert cal_found.name == cal_name, 'expected found calendar name to match'

    def test_delete_calendar(self, caldav):
        # create a new calendar then delete it and verify
        cal_name = f'{CALENDAR_PREFIX} {datetime.now()}'
        new_calendar = caldav.make_calendar(cal_name)

        time.sleep(TEST_SLEEP_1_SECOND)
        result = caldav.delete_calendar(new_calendar)
        assert result, 'expected to be able to delete calendar'

        time.sleep(TEST_SLEEP_1_SECOND)
        assert caldav.does_calendar_exist_by_id(new_calendar.id) is False, 'expected deleted calendar to not be found'

    def test_calendar_visible_multiple_clients(self, caldav):
        # add a new calendar with one client, verify the calendar is sync'd/seen with 2nd client
        # our first caldav client is the one provided by the fixture; we'll create a second one
        second_caldav_client = CalDAV(TEST_CALDAV_URL, CONNECT_TIMEOUT)
        login_success = second_caldav_client.login(TEST_ACCT_1_USERNAME, TEST_ACCT_1_PASSWORD)
        assert login_success, 'expected to be able to connect to caldav server'

        # create a new calendar with our first caldav client
        cal_name = f'{CALENDAR_PREFIX} created by first client {datetime.now()}'
        test_cal = caldav.make_calendar(cal_name)

        # now search for event with the second caldav client and ensure it is found
        time.sleep(TEST_SLEEP_1_SECOND)
        cal_found = second_caldav_client.get_calendar_by_name(cal_name)
        assert cal_found, 'expected second caldav client to be able to find calendar by name'

        # delete the calendar with the second caldav client
        result = second_caldav_client.delete_calendar(test_cal)
        assert result, 'expected to be able to delete the calendar using second caldav client'

        # now search for the calendar with the first caldav client and it shouldn't be found
        time.sleep(TEST_SLEEP_1_SECOND)
        found = second_caldav_client.get_calendar_by_name(cal_name)
        assert not found, (
            'expected the calendar to not be found by first caldav client after it was deleted by the second client'
        )

        # done with our second client
        second_caldav_client.logout()
