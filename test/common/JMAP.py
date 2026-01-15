import gevent
import json
import requests
import time

from common.logger import log

from locust import events
from jmapc import Client, EmailQueryFilterCondition, MailboxQueryFilterCondition, Ref

from jmapc.methods import (
    CoreEcho,
    CoreEchoResponse,
    EmailGet,
    EmailGetResponse,
    EmailQuery,
    EmailQueryResponse,
    IdentityGet,
    IdentityGetResponse,
    MailboxQuery,
    MailboxQueryResponse,
    MailboxGet,
    MailboxGetResponse,
)


class JMAP:
    def __init__(self, host, username, password, locust=False):
        self.client = self._get_client(host, username, password)
        self.account_id = self.client.account_id
        self.host = host
        self.username = username
        self.password = password
        self.locust = locust

        # grab our JMAP server's api_url and identity id for when we send JMAP api requests directly
        session = self.get_session()
        self.api_url = session.api_url
        self.identity_id = self.get_identity()[0].id

    def _get_client(self, host, username, password):
        """
        Create a JMAP client used to send JMAP requests.
        """
        client = None
        log.debug(f'creating jmap client for host: {host}')

        try:
            client = Client.create_with_password(
                host,
                username,
                password,
            )
        except Exception as e:
            log.debug('failed creating JMAP client')
            log.debug(f'caught exception: {str(e)}')

        return client

    def get_session(self):
        """
        Return the current JMAP session info.
        """
        log.debug('retrieving jmap session info')
        return self.client.jmap_session

    def echo(self, echo_data):
        """
        Echo to test jmap connection.
        """
        method = CoreEcho(data=echo_data)

        # call JMAP API with the method
        log.debug(f'calling jmap echo with: {echo_data}')
        result = self.client.request(method)

        assert isinstance(result, CoreEchoResponse), f'expected a CoreEchoResponse but got {type(result)}'
        assert result.data, 'expected echo response data'
        log.debug(f'received echo back: {result.data}')
        return result.data

    def get_identity(self):
        """
        Perform IdentityGet request.
        """
        method = IdentityGet()

        # call JMAP API with the method
        log.debug('getting jmap identity')

        try:
            result = self.client.request(method)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert isinstance(result, IdentityGetResponse), f'expected an IdentityGetResponse but got {type(result)}'
        return result.data

    def request(self, request_payload):
        """
        Send a JMAP HTTP request directly to our JMAP server (not using the JMAPC module) with the provided
        request_payload containing the JMAP request details.
        """
        headers = {
            'Authorization': 'Basic',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

        # now send our request to our jmap server; we are getting the api_url from our existing jmapc client session
        # even though we are sending the actual JMAP request directly not via the jmapc module
        response = requests.post(
            self.api_url, headers=headers, auth=(self.username, self.password), data=json.dumps(request_payload)
        )

        result = response.json()
        assert result, 'expected jmap request to return response json'

        return result

    def query_mailboxes(self, query_params={}):
        """
        Send request to query mailboxes.
        """
        method = MailboxQuery(
            sort=query_params.get('sort'),  # returns None by default if doesn't exist
            position=query_params.get('position'),
            anchor=query_params.get('anchor'),
            anchor_offset=query_params.get('anchor_offset'),
            limit=query_params.get('limit'),
            calculate_total=query_params.get('calculate_total'),
            filter=query_params.get('filter'),
            sort_as_tree=query_params.get('sort_as_tree', False),
            filter_as_tree=query_params.get('filter_as_tree', False),
        )

        # call JMAP API with the method
        log.debug(f'querying jmap mailboxes with query params: {query_params}')
        try:
            result = self.client.request(method)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert isinstance(result, MailboxQueryResponse), f'expected a MailboxQueryResponse but got {type(result)}'
        assert result.account_id == self.client.account_id, 'expected correct account id'
        log.debug(f'query returned these mailbox ids: {result.ids}')

        return result

    def get_mailboxes_by_id(self, mailbox_ids=None):
        """
        Send request to get the details for the given mailbox ids; if no ids are provided then the
        get will return details for all the mailboxes.
        """
        method = MailboxGet(mailbox_ids)

        # call JMAP API with the method
        if mailbox_ids:
            log.debug(f'getting mailbox details for mailbox ids: {mailbox_ids}')
        else:
            log.debug('getting mailbox details for all mailboxes')

        try:
            result = self.client.request(method)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert isinstance(result, MailboxGetResponse), f'expected a MailboxGetResponse but got {type(result)}'
        assert result.account_id == self.client.account_id, 'expected correct account id'
        log.debug(f'received details for {len(result.data)} mailboxes')

        return result.data if result.data else None

    def get_mailbox_by_name(self, mailbox_name):
        """
        Using a single request with multiple methods, first query for the given mailbox name to get the mailbox
        id, then get the mailbox details for that mailbox (id).
        """
        methods = [
            MailboxQuery(filter=MailboxQueryFilterCondition(name=mailbox_name)),
            MailboxGet(ids=Ref('/ids')),
        ]

        log.debug(f'getting mailbox id and then details for mailbox: {mailbox_name}')
        try:
            results = self.client.request(methods)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert results, 'expected results from both the mailbox query and get'
        assert isinstance(results[0].response, MailboxQueryResponse), (
            f'expected a MailboxQueryResponse but got {type(results[0])}'
        )
        assert isinstance(results[1].response, MailboxGetResponse), (
            f'expected a MailboxGetResponse but got {type(results[1])}'
        )

        # if mailbox was found return the mailbox details, otherwise none
        if len(results[0].response.ids) != 1:
            log.debug(f'mailbox "{mailbox_name}" was not found')
            return None

        log.debug(f'mailbox "{mailbox_name}" found')
        return results[1].response.data

    def create_mailbox(self, mailbox_name, parent_id=None, is_subscribed=True):
        """
        Create a new mailbox with the given name, and parent (optional). Subscribe to it in case
        we want to manually see the new mailbox in an email client that supports JMAP.
        Note: We are not using JMAPC module's MailboxSet here because it is expecting some null
        return values which stalwart doesn't provide, and results in a 'keyerror: updated' in
        the jmapc module. So we will build and send our JMAP request directly ourselves.
        """
        mailbox_set_payload = {
            'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
            'methodCalls': [
                [
                    'Mailbox/set',
                    {
                        'accountId': self.account_id,
                        'create': {
                            'newMailbox': {
                                'name': mailbox_name,
                                'parentId': parent_id,
                                'isSubscribed': is_subscribed,
                            }
                        },
                    },
                    'c1',
                ]
            ],
        }

        log.debug(f"creating mailbox '{mailbox_name}' with parent id '{parent_id}' and is_subscribed {is_subscribed}")
        result = self.request(mailbox_set_payload)

        try:
            mailbox_created = result['methodResponses'][0][1]['created']
            log.debug(f"mailbox '{mailbox_name}' was created successfully: {mailbox_created}")
            return mailbox_created

        except Exception:
            log.debug(f'error creating mailbox: {result}')
            return result

    def rename_mailbox_by_id(self, mailbox_id, new_mailbox_name):
        """
        Update an existing mailbox's name using the given maibox id.
        Note: We are not using JMAPC module's MailboxSet here because it is expecting some null
        return values which stalwart doesn't provide, and results in a 'keyerror: updated' in
        the jmapc module. So we will build and send our JMAP request directly ourselves.
        """
        mailbox_set_payload = {
            'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
            'methodCalls': [
                [
                    'Mailbox/set',
                    {
                        'accountId': self.account_id,
                        'update': {
                            mailbox_id: {
                                'name': new_mailbox_name,
                            }
                        },
                    },
                    'u1',
                ]
            ],
        }

        log.debug(f"updating mailbox with id '{mailbox_id}' with new mailbox name '{new_mailbox_name}'")
        result = self.request(mailbox_set_payload)

        try:
            mailbox_update = result['methodResponses'][0][1]['updated']
            log.debug(f'mailbox was updated successfully: {mailbox_update}')
            return mailbox_update

        except Exception:
            log.debug(f"error updating mailbox with id '{mailbox_id}': {result}")
            return result

    def set_mailbox_subscribe_by_id(self, mailbox_id, is_subscribed):
        """
        Update an existing mailbox's is_subscribed status using the given maibox id.
        Note: We are not using JMAPC module's MailboxSet here because it is expecting some null
        return values which stalwart doesn't provide, and results in a 'keyerror: updated' in
        the jmapc module. So we will build and send our JMAP request directly ourselves.
        """
        mailbox_set_payload = {
            'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
            'methodCalls': [
                [
                    'Mailbox/set',
                    {
                        'accountId': self.account_id,
                        'update': {
                            mailbox_id: {
                                'isSubscribed': is_subscribed,
                            }
                        },
                    },
                    'u1',
                ]
            ],
        }

        log.debug(f"setting mailbox with id '{mailbox_id}' is_subscribed to {is_subscribed}")
        result = self.request(mailbox_set_payload)

        try:
            mailbox_update = result['methodResponses'][0][1]['updated']
            log.debug(f'mailbox was updated successfully: {mailbox_update}')
            return mailbox_update

        except Exception:
            log.debug(f"error updating mailbox with id '{mailbox_id}': {result}")
            return result

    def delete_mailbox_by_id(self, mailbox_id):
        """
        Delete the mailbox with the given id.
        """
        mailbox_set_payload = {
            'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
            'methodCalls': [
                [
                    'Mailbox/set',
                    {
                        'accountId': self.account_id,
                        'destroy': [mailbox_id],
                    },
                    'd1',
                ]
            ],
        }

        log.debug(f"deleting mailbox with id '{mailbox_id}'")
        result = self.request(mailbox_set_payload)

        try:
            mailbox_destroy = result['methodResponses'][0][1]['destroyed']
            log.debug(f'mailbox was deleted successfully: {mailbox_destroy}')
            return mailbox_destroy

        except Exception:
            log.debug(f"error deleting mailbox with id '{mailbox_id}': {result}")
            return result

    def query_email(self, filter=None, limit=None):
        """
        Perform an email query using the provided filter, and return the found email ids.
        """
        method = EmailQuery(
            collapse_threads=True,
            filter=filter,
            limit=limit,
        )

        log.debug(f'querying email with filter: {filter} and limit: {limit}')

        try:
            result = self.client.request(method)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert isinstance(result, EmailQueryResponse), f'expected an EmailQueryResponse but got {type(result)}'
        assert result.account_id == self.account_id, 'expected account id returned to be correct'
        log.debug(f'query has returned {len(result.ids)} email ids: {result.ids}')

        return result.ids

    def get_test_email_ids_from_inbox(self):
        """
        Query the inbox for test emails (test subject) and return a list of ids, or none if none exist.
        """
        mailbox_search = self.get_mailbox_by_name('Inbox')
        inbox_id = mailbox_search[0].id
        assert inbox_id, 'expected to get the inbox mailbox id'

        # our populate inbox has provided us with emails in the inbox
        filter = EmailQueryFilterCondition(in_mailbox=inbox_id)

        email_ids = self.query_email(filter)

        return email_ids if len(email_ids) >= 0 else None

    def get_email(self, list_of_email_ids):
        """
        Retrieve the email details for emails with the given id(s). Return the email details for the
        found emails, and also return a list of not found email ids.
        """
        method = EmailGet(ids=list_of_email_ids)

        log.debug(f'getting email for ids: {list_of_email_ids}')

        try:
            result = self.client.request(method)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        assert isinstance(result, EmailGetResponse), f'expected an EmailGetResponse but got {type(result)}'
        assert result.account_id == self.account_id, 'expected account id returned to be correct'

        found_emails = result.data if len(result.data) > 0 else None
        not_found_emails = result.not_found if len(result.not_found) > 0 else None
        log.debug(f'get email has found {len(result.data)} email(s), and NOT found {len(result.not_found)} email(s)')

        return found_emails, not_found_emails

    def create_draft_email(self, from_email, to_email, subject, plain_text_body, html_body=None):
        """
        Create a draft email to/from the given email addresses with the given subject and body.
        Note: We are not using JMAPC module's MailboxSet here because it is expecting some null
        return values which stalwart doesn't provide, and results in a 'keyerror: updated' in
        the jmapc module. So we will build and send our JMAP request directly ourselves.
        """
        email_create_payload = {
            'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
            'methodCalls': [
                [
                    'Email/set',
                    {
                        'accountId': self.account_id,
                        'create': {
                            'newEmail': {
                                'from': [{'email': from_email}],
                                'to': [{'email': to_email}],
                                'subject': subject,
                                'textBody': plain_text_body,
                                'htmlBody': html_body,
                                'mailboxIds': {
                                    'd': True,  # drafts folder
                                },
                                'keywords': {
                                    '$draft': True,
                                },
                            }
                        },
                    },
                    'e0',
                ]
            ],
        }

        log.debug(
            f"creating draft email from '{from_email.split('@')[0]} to '{to_email.split('@')[0]}' subject: {subject}"
        )
        create_result = self.request(email_create_payload)

        try:
            created_email_id = create_result['methodResponses'][0][1]['created']['newEmail']['id']
            log.debug(f'draft email was created successfully and has id: {created_email_id}')
            return created_email_id
        except Exception:
            log.debug(f'error creating email: {create_result}')
            return None

    def send_email(
        self, from_email, to_email, subject, cc_email=None, bcc_email=None, plain_text_body=None, html_body=None
    ):
        """
        Send an email to/from the given email addresses with the given subject and body.
        Note: We are not using JMAPC module's MailboxSet here because it is expecting some null
        return values which stalwart doesn't provide, and results in a 'keyerror: updated' in
        the jmapc module. So we will build and send our JMAP request directly ourselves.
        To send an email in JMAP first you create the object with an EmailSet request (ie. create
        an email in the 'Drafts' folder) and then you use the EmailSubmission request to actually
        send the email, which will also remove it from the 'Drafts' folder after it has been sent.
        """
        new_email = {
            'from': [{'email': from_email}],
            'to': [{'email': to_email}],
            'subject': subject,
            'mailboxIds': {
                'd': True,  # drafts folder
            },
        }

        if plain_text_body:
            new_email['bodyValues'] = {
                'text': {'value': plain_text_body, 'isEncodingProblem': False, 'charset': 'UTF-8'}
            }

        if html_body:
            new_email['htmlBody'] = html_body

        log_msg = f"from '{from_email.split('@')[0]}' to '{to_email.split('@')[0]}' with subject: '{subject}'"

        if cc_email:
            new_email['cc'] = [{'email': cc_email}]
            log_msg = log_msg + f" cc '{cc_email.split('@')[0]}'"

        if bcc_email:
            new_email['bcc'] = [{'email': bcc_email}]
            log_msg = log_msg + f" bcc '{bcc_email.split('@')[0]}'"

        email_create_payload = {
            'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail'],
            'methodCalls': [
                [
                    'Email/set',
                    {
                        'accountId': self.account_id,
                        'create': {
                            'newEmail': new_email,
                        },
                    },
                    'e0',
                ]
            ],
        }

        log.debug(f'creating a draft email {log_msg}')

        try:
            create_result = self.request(email_create_payload)
        except Exception as e:
            log.debug(f'caught exception: {str(e)}')

        try:
            created_email_id = create_result['methodResponses'][0][1]['created']['newEmail']['id']
            log.debug(f'draft email was created successfully and has id: {created_email_id}')
        except Exception as e:
            log.debug(f'error creating email: {e}')
            return False

        email_submit_payload = {
            'using': ['urn:ietf:params:jmap:core', 'urn:ietf:params:jmap:mail', 'urn:ietf:params:jmap:submission'],
            'methodCalls': [
                [
                    'EmailSubmission/set',
                    {
                        'accountId': self.account_id,
                        'onSuccessDestroyEmail': ['#newSubmission'],  # remove from drafts folder after sent
                        'create': {
                            'newSubmission': {
                                'emailId': created_email_id,
                                'identityId': self.identity_id,
                            }
                        },
                    },
                    'e1',
                ]
            ],
        }

        log.debug(f'sending the draft email {log_msg}')

        if self.locust:
            # locust uses gevent greenlets to run concurrent users in single process
            start_time = gevent.get_hub().loop.now()

        send_exception = None
        send_success = False
        send_result = self.request(email_submit_payload)

        try:
            sent = send_result['methodResponses'][0][1]['created']
            log.debug(f'email sent successfully: {sent}')
            send_success = True

        except Exception as e:
            log.debug(f"error sending the draft email with id '{created_email_id}': {send_result}")
            send_exception = str(e)

        # if running a locust load test we need to let locust know the jmap send is done
        if self.locust:
            events.request.fire(
                request_type='jmap',
                name='send_message',
                response_time=(gevent.get_hub().loop.now() - start_time) * 1000,  # convert to ms
                response_length=len(plain_text_body) if not send_exception else 0,
                context=None,
                exception=send_exception,
            )

        return send_success

    def wait_for_message_to_arrive(self, subject):
        """
        Check the inbox for a message to arrive with the given subject. If the message hasn't arrived yet wait
        for it; return the id of the message after it has arrived (or -1 if it never arrived).
        """
        max_checks = 18
        wait_seconds = 5
        arrived_msg_id = 0

        for checks in range(1, max_checks + 1):
            log.debug(
                f'waiting {wait_seconds} seconds for message to arrive in test_acct_1 inbox '
                f'(check {checks} of {max_checks})'
            )
            time.sleep(wait_seconds)

            search_filter = {
                'inMailbox': 'a',
                'subject': subject,
            }

            found_email_ids = self.query_email(filter=search_filter)

            if len(found_email_ids) == 1:
                arrived_msg_id = found_email_ids[0]
                break

        return arrived_msg_id
