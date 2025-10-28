import caldav
import requests
import time
import vobject
import xml.etree.ElementTree as ET

from urllib.parse import unquote

from common.const import (
    TEST_SLEEP_1_SECOND,
)

from common.logger import log


class CardDAV:
    def __init__(self, carddav_server_url, timeout):
        self.carddav_server_url = carddav_server_url
        self.carddav_server_host = self.carddav_server_url.split('/dav/card')[0]
        self.connection_timeout = timeout
        self.client = None
        self.principal = None
        self.auth = None

    def login(self, username, password):
        """
        Connect and sign in to the carddav server as defined in the .env.test file.
        """
        self.username = username
        self.password = password
        self.auth = requests.auth.HTTPBasicAuth(self.username, self.password)
        self.ab_url = f'{self.carddav_server_url}/{self.username}'
        success = False

        # create a carddav client; note that we use the caldav library to connect to cardav because the caldav module
        # doesn't offer direct carddav methods (but DAVClient uses webdav which carddav and caldav is built upon)
        self.client = caldav.DAVClient(
            url=self.ab_url,
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
            log.debug(f"connecting to carddav at '{self.carddav_server_url}' with username '{username.split('@')[0]}'")
            self.principal = self.client.principal()
            log.debug('successfully connected to carddav server')
            success = True

        except Exception as e:
            log.debug(f'failed to connect to carddav server: {e}')

        return success

    def logout(self):
        log.debug(f'closing carddav client session {self.username.split("@")[0]}')

        try:
            self.client.close()  # is no return value
        except Exception as e:
            log.debug(f'{str(e)}')

    def get_address_books(self):
        """
        Retrieve and return all of the address books that exist for our current signed-in carddav user. Note that we
        build and send our carddav (webdav) request ourself.
        """
        headers = {
            'Content-Type': 'application/xml; charset=utf-8',
            'Depth': '1',  # request direct children of the URL
        }

        # XML body for PROPFIND request to discover address books
        propfind_body = """<?xml version="1.0" encoding="utf-8" ?>
            <D:propfind xmlns:D="DAV:" xmlns:CS="http://calendarserver.org/ns/">
            <D:prop>
                <D:resourcetype/>
                <D:displayname/>
            </D:prop>
            </D:propfind>"""

        try:
            response = requests.request(
                'PROPFIND',
                url=self.ab_url,
                headers=headers,
                data=propfind_body,
                auth=self.auth,
                verify=True,  # set to False if you have SSL certificate issues (not recommended for production)
            )
            response.raise_for_status()  # raise an exception for bad status codes

            # now parse out the address books returned in the response
            address_books = []
            root = ET.fromstring(response.content)

            # namespace dictionary for easier parsing
            ns = {'D': 'DAV:', 'CS': 'http://calendarserver.org/ns/', 'C': 'urn:ietf:params:xml:ns:carddav'}

            # iterate through the response to find address books
            for response_node in root.findall('D:response', ns):
                href = response_node.find('D:href', ns)
                propstat = response_node.find('D:propstat', ns)
                if href is not None and propstat is not None:
                    resourcetype = propstat.find('D:prop/D:resourcetype', ns)
                    if resourcetype is not None and resourcetype.find('C:addressbook', ns) is not None:
                        displayname_node = propstat.find('D:prop/D:displayname', ns)
                        displayname = (
                            displayname_node.text if displayname_node is not None else href.text.split('/')[-2]
                        )  # Fallback to URL segment
                        address_books.append({'href': href.text, 'displayname': displayname})

            log.debug(f'found {len(address_books)} address book(s):')
            for found_ab in address_books:
                log.debug(f'{unquote(found_ab["displayname"])}')

            return address_books

        except requests.exceptions.RequestException as e:
            log.debug(f'error getting address books: {e}')
            return []

    def get_address_book_by_name(self, address_book_name):
        """
        Check if an address book exists that has the given name, and if so return it.
        """
        log.debug(f'getting address book by name: {address_book_name}')
        all_abs = self.get_address_books()
        for ab in all_abs:
            if unquote(ab['displayname']) == address_book_name:
                log.debug(f'found address book: {address_book_name}')
                return ab

        log.debug(f'address book does not exist: {address_book_name}')
        return None

    def does_address_book_exist(self, address_book_name):
        """
        Check if an address book exists that has the given name.
        """
        if self.get_address_book_by_name(address_book_name) is not None:
            return True
        return False

    def create_address_book(self, address_book_name):
        """
        Create a new address book with the given name. We build and send the carddav (webdav) request
        directly ourself.
        """
        log.debug(f'creating address book: {address_book_name}')

        new_ab_url = f'{self.ab_url}/{address_book_name}/'

        headers = {
            'Content-Type': 'application/xml; charset=utf-8',
            'Depth': '0',  # Depth 0 for creating the collection itself
        }

        mkcol_body = """<?xml version="1.0" encoding="utf-8" ?>
        <D:mkcol xmlns:D="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
        <D:set>
            <D:prop>
            <D:resourcetype>
                <D:collection/>
                <card:addressbook/>
            </D:resourcetype>
            </D:prop>
        </D:set>
        </D:mkcol>
        """

        try:
            response = requests.request(
                'MKCOL',
                url=new_ab_url,
                headers=headers,
                data=mkcol_body,
                auth=self.auth,
                verify=True,
            )

            response.raise_for_status()  # raise an exception for bad status codes

        except requests.exceptions.RequestException as e:
            log.debug(f'error creating address book: {e}')
            return False

        log.debug('address book created successfully')
        return True

    def delete_address_book_by_href(self, address_book_href):
        """
        Delete the given address book (href). When deleting an AB we must provide the full URL including protocol.
        """
        log.debug(f'deleting address book: {unquote(address_book_href)}')

        try:
            full_ab_url = f'{self.carddav_server_host}{address_book_href}'
            response = requests.delete(full_ab_url, auth=self.auth)
            response.raise_for_status()  # raise an exception for bad status codes

        except Exception as e:
            log.debug(f'error deleting address book: {e}')
            return False

        log.debug('address book successfully deleted')
        return True

    def delete_address_book_by_name(self, address_book_name):
        """
        Search for an address book by the given name and then delete it.
        """
        ab_to_del = self.get_address_book_by_name(address_book_name)
        if ab_to_del:
            success = self.delete_address_book_by_href(ab_to_del['href'])
            return success
        else:
            log.debug('unable to delete the address book because it does not exist')
            return False

    def cleanup_test_address_books(self, address_book_prefix):
        """
        Find all existing carddav address books with a name that match the given prefix and delete them.
        """
        existing_abs = self.get_address_books()

        if existing_abs:
            for ab in existing_abs:
                if address_book_prefix in unquote(ab['displayname']):
                    try:
                        self.delete_address_book_by_href(ab['href'])
                        time.sleep(TEST_SLEEP_1_SECOND)

                    except Exception as _ex:
                        # we don't really care if it failed for some reason as just cleaning up
                        pass

    def get_all_contacts(self, address_book_href):
        """
        Retrieve and return a list of the contacts that exist in the given address book. This returns a list
        of existing contacts (contact .vcf files) in the address book, not the details of each contact.
        """
        log.debug(f'retrieving list of contacts in adress book: {address_book_href}')
        contacts_list = []

        headers = {
            'Depth': '1',  # get contacts inside the address book resource
            'Content-Type': 'application/xml',
        }

        full_ab_url = f'{self.carddav_server_host}{address_book_href}'

        propfind_body = """<?xml version="1.0" encoding="UTF-8"?>
        <d:propfind xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
        <d:prop>
            <d:getetag/>
            <card:address-data/>
        </d:prop>
        </d:propfind>
        """

        try:
            response = requests.request(
                'PROPFIND',
                full_ab_url,
                data=propfind_body,
                headers=headers,
                auth=self.auth,
                verify=True,
            )

            response.raise_for_status()  # raise an exception for bad status codes

            # now parse out the raw contact vcard data returned in the response
            root = ET.fromstring(response.content)

            # namespace dictionary for easier parsing
            ns = {'D': 'DAV:', 'B': 'urn:ietf:params:xml:ns:carddav'}

            # iterate through the response to find address books
            for response_node in root.findall('D:response', ns):
                href = response_node.find('D:href', ns)
                if href is not None:
                    # first one is address book name; rest are .vcf contact cards, we only want the cards
                    if '.vcf' in href.text:
                        contacts_list.append(href.text)

            log.debug(f'found {len(contacts_list)} contact(s):')
            for found_contact in contacts_list:
                log.debug(found_contact)

        except requests.exceptions.RequestException as e:
            log.debug(f'error retrieving contacts list: {e}')

        return contacts_list

    def get_contact_details(self, contact_href):
        """
        Retrieve and return the details for the given contact (.vcf file). Contact details are returned as
        a contacts vCard object.
        """
        log.debug(f'retrieving contact details for contact: {contact_href}')
        contact_vcard = None

        headers = {'Depth': '1', 'Content-Type': 'application/xml'}

        full_contact_url = f'{self.carddav_server_host}{contact_href}'

        propfind_body = """<?xml version="1.0" encoding="UTF-8"?>
        <d:propfind xmlns:d="DAV:" xmlns:card="urn:ietf:params:xml:ns:carddav">
        <d:prop>
            <d:getetag/>
            <card:address-data/>
        </d:prop>
        </d:propfind>
        """

        try:
            response = requests.request(
                'PROPFIND',
                full_contact_url,
                data=propfind_body,
                headers=headers,
                auth=self.auth,
                verify=True,
            )

            response.raise_for_status()  # raise an exception for bad status codes

            # now parse out the raw contact vcard data returned in the response
            root = ET.fromstring(response.content)

            # namespace dictionary for easier parsing
            ns = {'D': 'DAV:', 'B': 'urn:ietf:params:xml:ns:carddav'}

            # get the contact vCard data
            for response_node in root.findall('D:response', ns):
                propstat = response_node.find('D:propstat', ns)
                if propstat is not None:
                    data = propstat.find('D:prop/B:address-data', ns)
                    if data is not None:
                        # if want to see raw vCard data uncomment next line
                        # log.debug(f'raw contact vCard: {data.text}')
                        # now convert from raw vCard string to vCard object
                        contact_vcard = vobject.readOne(data.text)

            log.debug(f'found contact details: {contact_vcard}')

        except requests.exceptions.RequestException as e:
            log.debug(f'error retrieving contact details: {e}')

        return contact_vcard

    def create_contact(self, address_book_href, contact_data):
        """
        Create a new contact in the given address book, using the given contact details.
        """
        full_ab_url = f'{self.carddav_server_host}{address_book_href}'
        contact_name = f'{contact_data.get("first_name", "First")}-{contact_data.get("last_name", "Last")}'.lower()
        new_contact_url = f'{full_ab_url}{contact_name}.vcf'
        log.debug(f'creating new contact: {new_contact_url}')

        # create our contact vCard
        vcard = vobject.vCard()
        vcard.add('n')
        vcard.n.value = vobject.vcard.Name(family=contact_data['last_name'], given=contact_data['first_name'])
        vcard.add('fn')
        vcard.fn.value = contact_data['full_name']

        if 'email_home' in contact_data:
            email = vcard.add('email')
            email.value = contact_data['email_home']
            email.type_param = 'HOME'

        if 'email_work' in contact_data:
            email = vcard.add('email')
            email.value = contact_data['email_work']
            email.type_param = 'WORK'

        if 'tel_cell' in contact_data:
            tel = vcard.add('tel')
            tel.value = contact_data['tel_cell']
            tel.type_param = 'CELL'

        if 'tel_work' in contact_data:
            tel = vcard.add('tel')
            tel.value = contact_data['tel_work']
            tel.type_param = 'WORK'

        if 'nickname' in contact_data:
            nickname = vcard.add('nickname')
            nickname.value = contact_data['nickname']

        if 'website' in contact_data:
            ws = vcard.add('url')
            ws.value = contact_data['website']
            ws.type_param = 'WEBSITE'

        if 'note' in contact_data:
            note = vcard.add('note')
            note.value = contact_data['note']

        if 'address' in contact_data:
            adr = vcard.add('adr')
            adr.type_param = 'HOME'
            adr.value = vobject.vcard.Address(
                street=contact_data['address']['street'],
                city=contact_data['address']['city'],
                region=contact_data['address']['region'],
                code=contact_data['address']['code'],
                country=contact_data['address']['country'],
            )

        # now actually build the vCard
        vcard_string = vcard.serialize()

        # send a PUT request to the server with the vCard data
        try:
            response = requests.put(
                new_contact_url,
                data=vcard_string,
                auth=self.auth,
                headers={
                    'Content-Type': 'text/vcard; charset=utf-8',
                    'If-None-Match': '*',  # Ensures we are creating a new contact and not overwriting an existing one
                },
                verify=True,  # Set to False if you use a self-signed certificate (not recommended)
            )

            response.raise_for_status()  # raise an exception for bad status codes

        except requests.exceptions.RequestException as e:
            log.debug(f'error creating contact: {e}')
            return None

        log.debug('contact created successfully')
        return True

    def update_contact(self, address_book_href, contact_href, contact_vcard):
        """
        Update the given contact's data. Receives the address book, contact href, and contact data in the form
        of a vCard object.
        """
        full_contact_url = f'{self.carddav_server_host}{contact_href}'
        log.debug(f'updating existing contact: {contact_href}')

        # send a PUT request to the server with the updated vCard data
        try:
            vcard_str = contact_vcard.serialize().strip()
            response = requests.put(
                full_contact_url,
                data=vcard_str,
                auth=self.auth,
                headers={
                    'Content-Type': 'text/vcard; charset=utf-8',
                },
                verify=True,  # Set to False if you use a self-signed certificate (not recommended)
            )

            response.raise_for_status()  # raise an exception for bad status codes

        except requests.exceptions.RequestException as e:
            log.debug(f'error updating contact: {e}')
            return False

        log.debug('contact updated successfully')
        return True

    def delete_contact_by_href(self, contact_href):
        """
        Delete the given contact (by href). When deleting a contact we must provide the full URL including protocol.
        """
        log.debug(f'deleting contact: {unquote(contact_href)}')

        try:
            full_contact_url = f'{self.carddav_server_host}{contact_href}'
            response = requests.delete(full_contact_url, auth=self.auth)
            response.raise_for_status()  # raise an exception for bad status codes

        except Exception as e:
            log.debug(f'error deleting contact: {e}')
            return False

        log.debug('contact successfully deleted')
        return True
