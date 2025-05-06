from email.message import EmailMessage
from smtplib import SMTP_SSL

from common.logger import log

from const import (
    TEST_SERVER_HOST,
    SMTP_PORT,
    CONNECT_TIMEOUT,
    TEST_ACCT_1_EMAIL,
    TEST_ACCT_2_EMAIL,
    TEST_MSG_BODY_PREFIX,
    TEST_MSG_ATTACHMENT,
)


class SMTP:
    def __init__(self):
        self.connection = None

    def login(self, username, password):
        """
        Connect and log into the smtp server as defined in the .env.test file.
        """
        success = False
        log.debug(f'connecting to smtp host: {TEST_SERVER_HOST}')

        try:
            self.connection = SMTP_SSL(TEST_SERVER_HOST, SMTP_PORT, timeout=CONNECT_TIMEOUT)
            self.connection.set_debuglevel(0) # set to 1 if want to debug locally
            log.debug('connected, now signing in to smtp')
            result, data = self.connection.login(username, password)
            log.debug(f'{result}, {data}')
            if b'Authentication succeeded' in data:
                log.debug(f'successfully signed into smtp host: {TEST_SERVER_HOST}')
                success = True

        except Exception as e:
            log.debug(f'{str(e)}')

        return success

    def logout(self):
        log.debug(f'logging out of SMTP host: {TEST_SERVER_HOST}')
        result, data = self.connection.quit()
        log.debug(f'{result}, {data}')
        if b'Bye' in data:
            return True
        return False

    def send_test_email(self, subject, add_attachment=False):
        # send an email to test_acct_1 (from test_acct_2) using smtp
        body = TEST_MSG_BODY_PREFIX
        msg = EmailMessage()

        msg['To'] = TEST_ACCT_1_EMAIL
        msg['From'] = TEST_ACCT_2_EMAIL
        msg['Subject'] = subject
        msg.set_content(body)

        if add_attachment:
            log.debug('adding an attachment to the test email')
            with open(TEST_MSG_ATTACHMENT, 'rb') as fp:
                try:
                    img_data = fp.read()
                except Exception as e:
                    log.debug(f'{str(e)}')
            msg.add_attachment(img_data, maintype='image', subtype='png')

        log.debug(f'sending an email from test_acct_2 to test_acct_1 with the subject: {subject}')
        try:
            self.connection.send_message(msg)
        except Exception as e:
            log.debug(f'failed to send email: {str(e)}')
            return False

        return True
