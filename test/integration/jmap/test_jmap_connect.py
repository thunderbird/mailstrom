from common.logger import log

from const import (
    TEST_SERVER_HOST,
    JMAP_PORT,
    TEST_ACCT_1_USERNAME,
    TEST_ACCT_1_EMAIL,
    JMAP_CAPABILITY_CORE_MAX_SIZE_UPLOAD,
    JMAP_CAPABILITY_CORE_MAX_CONCURRENT_UPLOAD,
    JMAP_CAPABILITY_CORE_MAX_SIZE_REQUEST,
    JMAP_CAPABILITY_CORE_MAX_CONCURRENT_REQUESTS,
    JMAP_CAPABILITY_CORE_MAX_CALLS_IN_REQUEST,
)


class TestJMAPConnect:
    def test_get_session(self, jmap_acct_1):
        # jmap_acct_1 session is provided after authentication to the jmap_acct_1 server by the jmap_acct_1 client; the
        # session provides data and capabilities that the server can provide to the client for the given credentials
        session = jmap_acct_1.get_session()
        assert session.username == TEST_ACCT_1_USERNAME, 'expected jmap session.username to be correct'

        exp_api_url = f'https://{TEST_SERVER_HOST}:{JMAP_PORT}/jmap/'
        assert session.api_url == exp_api_url, 'expected jmap_acct_1 session api_url to be correct'
        assert f'{exp_api_url}download/' in session.download_url, 'expected jmap session download_url to be correct'
        assert f'{exp_api_url}upload/' in session.upload_url, 'expected jmap session upload_url to be correct'
        assert f'{exp_api_url}eventsource/' in session.event_source_url, (
            'expected jmap_acct_1 session event_source_url to be correct'
        )

        assert session.state, 'expected jmap_acct_1 session state'

        assert session.primary_accounts.mail == jmap_acct_1.account_id, (
            'expected jmap_acct_1 session primary account mail id to be correct'
        )
        assert session.primary_accounts.submission == jmap_acct_1.account_id, (
            'expected jmap_acct_1 session primary account submission id to be correct'
        )

        assert session.capabilities.core, 'expected session core capabilities'
        assert session.capabilities.core.max_size_upload == JMAP_CAPABILITY_CORE_MAX_SIZE_UPLOAD, (
            'expected jmap_acct_1 session core capability max_size_upload to be correct'
        )
        assert session.capabilities.core.max_concurrent_upload == JMAP_CAPABILITY_CORE_MAX_CONCURRENT_UPLOAD, (
            'expected jmap_acct_1 session core capability max_concurrent_upload to be correct'
        )
        assert session.capabilities.core.max_size_request == JMAP_CAPABILITY_CORE_MAX_SIZE_REQUEST, (
            'expected jmap_acct_1 session core capability max_size_request to be correct'
        )
        assert session.capabilities.core.max_concurrent_requests == JMAP_CAPABILITY_CORE_MAX_CONCURRENT_REQUESTS, (
            'expected jmap_acct_1 session core capability max_concurrent_requests to be correct'
        )
        assert session.capabilities.core.max_calls_in_request == JMAP_CAPABILITY_CORE_MAX_CALLS_IN_REQUEST, (
            'expected jmap_acct_1 session core capability max_calls_in_request to be correct'
        )

        assert session.capabilities.extensions, 'expected sesssion capabilities extensions'
        assert session.capabilities.extensions['urn:ietf:params:jmap:websocket']['url'], (
            'expected websocket extension to exist in jmap_acct_1 session capabilities'
        )
        exp_ws_url = f'wss://{TEST_SERVER_HOST}:{JMAP_PORT}/jmap/ws'
        assert session.capabilities.extensions['urn:ietf:params:jmap:websocket']['url'] == exp_ws_url, (
            'expected websocket extension url to be correct'
        )

    def test_echo(self, jmap_acct_1):
        # do an echo to verify that we have a valid authenticated session
        echo_data = {
            'testing': 123,
        }
        echo_back = jmap_acct_1.echo(echo_data)
        assert echo_back == echo_data, 'expected echo to return the same data'

    def test_get_account_id(self, jmap_acct_1):
        # account id represents a user's account within the jmap_acct_1 system and contains a collection of data
        # (ie. email, contacts, calendars); an account belongs to a user but each user may have more than
        # one account; the account id is used in jmap_acct_1 requests (jmap_acct_1c module adds it to requests for us)
        log.debug(f'account id: {jmap_acct_1.account_id}')
        assert jmap_acct_1.account_id is not None
        assert len(jmap_acct_1.account_id) > 0

    def test_get_identity(self, jmap_acct_1):
        # identity id represents a specific identity (ie. an email address, a phone number) within a jmap_acct_1 acct;
        # a user can have multiple identities associated with their account (ie. multiple email addresses)
        result = jmap_acct_1.get_identity()
        assert result is not None, 'expected getIdentity to return identity data'

        # we only expect one identity to exist for our test account (one thundermail email address)
        assert len(result) == 1, 'expected 1 jmap_acct_1 identity to be returned'
        identity = result[0]
        log.debug(f'received jmap_acct_1 identity id: {identity.id}')

        assert identity.name == TEST_ACCT_1_USERNAME, 'expected identity.name to be correct'
        assert identity.email == TEST_ACCT_1_EMAIL, 'expected identity.email to be correct'
        assert identity.reply_to is None, 'expected identity.reply_to to be none'
        assert identity.bcc is None, 'expected identity.bcc to be none'
        assert len(identity.text_signature) == 0, 'expected identity.text_signature to be empty'
        assert len(identity.html_signature) == 0, 'expected identity.html_signature to be empty'
        assert identity.may_delete, 'expected identity.may_delete to be true'
        assert identity.id is not None, 'expected identity.id to exist'
        assert len(identity.id) > 0, 'expected len identity.id to be > 0'
