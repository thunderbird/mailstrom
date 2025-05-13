import gevent
import os
import sys

from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage

from smtplib import SMTP_SSL

from locust import events

# since we are calling locust cmd line we need to add common to path
sys.path.append('./')
from common.logger import log


class SMTP:
    def __init__(self, host, port, timeout, locust=False):
        self.connection = None
        self.host = host
        self.port = port
        self.connection_timeout = timeout
        self.locust = locust

    def login(self, username, password):
        """
        Connect and log into the smtp server as defined in the .env.test file.
        """
        success = False
        log.debug(f'connecting to smtp host: {self.host}')

        try:
            self.connection = SMTP_SSL(self.host, self.port, timeout=self.connection_timeout)
            self.connection.set_debuglevel(0)  # set to 1 if want to debug locally
            log.debug('connected, now signing in to smtp')
            result, data = self.connection.login(username, password)
            log.debug(f'{result}, {data}')
            if b'Authentication succeeded' in data:
                log.debug(f'successfully signed into smtp host: {self.host}')
                success = True

        except Exception as e:
            log.debug(f'{str(e)}')

        return success

    def logout(self):
        log.debug(f'logging out of SMTP host: {self.host}')
        result, data = self.connection.quit()
        log.debug(f'{result}, {data}')
        return True if b'Bye' in data else False

    def send_test_email(self, to_email, from_email, subject, body, attachment):
        # send a plain text email using smtp
        send_exception = None
        msg = EmailMessage()

        msg['To'] = to_email
        msg['From'] = from_email
        msg['Subject'] = subject
        msg.set_content(body)

        if attachment:
            log.debug('adding an attachment to the test email')
            with open(attachment, 'rb') as fp:
                try:
                    img_data = fp.read()
                except Exception as e:
                    log.debug(f'{str(e)}')
            msg.add_attachment(img_data, maintype='image', subtype='png')

        log.debug(f'sending an email from {from_email[:3]}*** to {to_email[:3]}*** with the subject: {subject}')

        if self.locust:
            # locust uses gevent greenlets to run concurrent users in single process
            start_time = gevent.get_hub().loop.now()

        try:
            self.connection.send_message(msg)

        except Exception as e:
            if 'Rate limit exceeded' in str(e):
                log.debug('failed to send email: rate limit exceeded')
                send_exception = 'rate limit exceeded'
            else:
                log.debug(f'failed to send email: {type(e)}')
                send_exception = type(e).__name__

        # if running a locust load test we need to let locust know the smtp send worked
        if self.locust:
            events.request.fire(
                request_type='smtp',
                name='send_message',
                response_time=(gevent.get_hub().loop.now() - start_time) * 1000,  # convert to ms
                response_length=len(body) if not send_exception else 0,
                context=None,
                exception=send_exception,
            )

        return send_exception

    def send_test_email_multipart(
        self, to_email, from_email, cc_email, bcc_email, subject, plain_body, html_body, attachment, priority=False
    ):
        # send a multipart email with plain text body or html body or both
        send_exception = None
        msg = MIMEMultipart()

        msg['From'] = from_email
        msg['To'] = to_email
        all_recipients = [to_email]
        log_txt = f'sending an email from {from_email[:3]}*** to {to_email[:3]}***'

        msg['Subject'] = subject

        if cc_email:
            msg['CC'] = cc_email
            all_recipients.append(cc_email)
            log_txt += f' cc {cc_email[:3]}***'

        if bcc_email:
            msg['BCC'] = bcc_email
            all_recipients.append(bcc_email)
            log_txt += f' bcc {bcc_email[:3]}***'

        if plain_body:
            msg.attach(MIMEText(plain_body, 'plain'))

        if html_body:
            msg.attach(MIMEText(html_body, 'html'))

        if priority:
            msg['X-Priority'] = '1'

        if attachment:
            log.debug('adding an attachment to the test email')

            with open(attachment, 'rb') as fp:
                try:
                    image = MIMEImage(fp.read(), name=os.path.basename(attachment))
                    msg.attach(image)
                except Exception as e:
                    send_exception = type(e).__name__
                    log.debug(f'{str(e)}')

        log.debug(f'{log_txt} with the subject: {subject}')

        try:
            self.connection.sendmail(from_email, all_recipients, msg.as_string())

        except Exception as e:
            if 'Rate limit exceeded' in str(e):
                log.debug('failed to send email: rate limit exceeded')
                send_exception = 'rate limit exceeded'
            else:
                log.debug(f'failed to send email: {type(e)}')
                log.debug(e)
                send_exception = type(e).__name__

        return send_exception
