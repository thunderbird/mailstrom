import pytest
import requests

from const import (
    TEST_CALDAV_RSVP_URL,
    CONNECT_TIMEOUT,
)


class TestCaldavRsvp:
    @pytest.mark.sanity
    def test_rsvp_endpoint_is_allowlisted(self):
        """The CalDAV scheduling RSVP page (/calendar/rsvp) must be reachable.

        Stalwart's ``http.allowed-endpoint`` rule is a deny-by-default allowlist built from the
        cluster's enabled ``https_features``. If ``/calendar/rsvp`` is missing from that allowlist,
        Stalwart returns 404 for the "Yes/No/Maybe" links in calendar invitation emails (see
        thunderbird/mailstrom#223). This guards against that regression.

        The endpoint is anonymous, so no credentials are needed. A bare GET (without the ``?i=``
        token) still proves the path is allowlisted: the regression signal is specifically a 404
        from the allowlist gate, so any non-404 status passes.
        """
        resp = requests.get(TEST_CALDAV_RSVP_URL, timeout=CONNECT_TIMEOUT)
        assert resp.status_code != 404, (
            f'{TEST_CALDAV_RSVP_URL} returned 404 — /calendar/rsvp is not allowlisted in Stalwart '
            f'http.allowed-endpoint (got {resp.status_code}); calendar invitation RSVP links will break'
        )
