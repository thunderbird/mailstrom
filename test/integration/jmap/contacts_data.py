# contacts test data for jmap contacts tests
JMAP_TEST_CONTACTS = [
    {
        'name': {
            'components': [{'kind': 'given', 'value': 'Indiana'}, {'kind': 'surname', 'value': 'Jones'}],
            'isOrdered': True,
        },
        'emails': {
            '0': {'contexts': {'work': True}, 'address': 'indianajones@example.org'},
        },
    },
    {
        'name': {
            'components': [{'kind': 'given', 'value': 'James'}, {'kind': 'surname', 'value': 'Bond'}],
            'isOrdered': True,
        },
        'emails': {
            '0': {'contexts': {'work': True}, 'address': 'jamesbond007@example.org'},
        },
    },
    {
        'name': {
            'components': [{'kind': 'given', 'value': 'E'}, {'kind': 'surname', 'value': 'T'}],
            'isOrdered': True,
        },
        'phones': {
            'phone0': {'number': '+1 555 0101', 'features': {'mobile': True}, '@type': 'Phone'},
        },
    },
    {
        'name': {
            'components': [{'kind': 'given', 'value': 'Jane'}, {'kind': 'surname', 'value': 'Bond'}],
            'isOrdered': True,
        },
        'emails': {
            '0': {'contexts': {'private': True}, 'address': 'janebond-home@example.org'},
            '1': {'contexts': {'work': True}, 'address': 'janebond-work@example.org'},
            '2': {'contexts': {'other': True}, 'address': 'janebond-other@example.org'},
            '3': {
                'contexts': {'custom': True},
                'label': 'Custom email',
                'address': 'janebond-custom@example.org',
            },
        },
    },
    {
        'name': {
            'components': [{'kind': 'given', 'value': 'Jerry'}],
        },
        'emails': {
            '0': {'contexts': {'work': True}, 'address': 'jerry@jerry-fake.org'},
        },
        'notes': {'n1': {'note': 'Created by integration tests. This contact only has a first name.'}},
    },
    {
        'name': {
            'components': [{'kind': 'given', 'value': 'Fire'}, {'kind': 'surname', 'value': 'Fox'}],
            'isOrdered': True,
        },
        'emails': {
            '0': {'contexts': {'work': True}, 'address': 'firefox@fakedomainexample.com'},
        },
        'phones': {
            'phone1': {'number': '+1 555 7777', 'features': {'work': True}, '@type': 'Phone'},
        },
    },
    {
        'name': {'full': 'Jane Doe'},
        'organizations': {
            'organization0': {
                'name': 'Jane Inc.',
                'units': [{'name': 'Toronto Team', '@type': 'OrgUnit'}],
                'contexts': {'work': True},
                '@type': 'Organization',
            }
        },
        'links': {
            'link0': {'uri': 'https://personalsite.com', 'contexts': {'private': True}, '@type': 'Link'},
            'link1': {'uri': 'https://worksite.com', 'contexts': {'work': True}, '@type': 'Link'},
            'link2': {'uri': 'https://customsite.com', 'label': 'Custom site', '@type': 'Link'},
        },
        'titles': {
            'title0': {'name': 'CEO', 'kind': 'title', '@type': 'Title', 'organizationId': 'organization0'},
        },
        'emails': {
            'email0': {
                'address': 'homeemail@madeupfakedomain.com',
                'contexts': {'private': True},
                'pref': 1,
                '@type': 'EmailAddress',
            },
            'email1': {
                'address': 'workemail@madeupfakedomain.com',
                'contexts': {'work': True},
                '@type': 'EmailAddress',
            },
            'email2': {'address': 'otheremail@madeupfakedomain.com', '@type': 'EmailAddress'},
            'email3': {'address': 'customemail@madeupfakedomain.com', 'label': 'Custom email', '@type': 'EmailAddress'},
        },
        'notes': {
            'note0': {'note': 'This is notes field 1.', '@type': 'Note'},
            'note1': {'note': 'This is notes field 2.', '@type': 'Note'},
        },
        'anniversaries': {
            'date0': {
                'date': {'@type': 'PartialDate', 'year': 2000, 'month': 1, 'day': 30},
                'kind': 'birth',
                '@type': 'Anniversary',
            }
        },
        'phones': {
            'phone0': {'number': '+1 555 0000', 'contexts': {'private': True}, '@type': 'Phone'},
            'phone1': {'number': '+1 555 1111', 'contexts': {'work': True}, '@type': 'Phone'},
            'phone2': {'number': '+1 555 2222', 'features': {'mobile': True}, '@type': 'Phone'},
            'phone3': {'number': '+1 555 3333', 'label': 'Custom phone', '@type': 'Phone'},
        },
    },
]
