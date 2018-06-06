import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import Encoders


class SMTPClient(object):
    def __init__(self, user, password, recipients):
        """SMTP Client for sending test results

        :param str user: user address from which will be sent emails
        :param str password: password for the user
        :param str|list[str] recipients: recipient or recepients of the emails
        """

        self.user = user
        self.password = password
        self.recipients = recipients if isinstance(recipients, list) else [recipients]

        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = smtplib.SMTP('smtp.office365.com', 587)
            self._session.starttls()
            self._session.login(self.user, self.password)

        return self._session

    def send_email(self, subject, text, log_msg):
        """Sends email

        :param str subject: email subject
        :param str text: email text
        :param str log_msg: shell tests logs
        """

        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = ', '.join(self.recipients)
        msg['Subject'] = subject

        msg.attach(MIMEText(text, 'plain'))

        log_part = MIMEBase('application', 'octet-stream')
        log_part.set_payload(log_msg)
        Encoders.encode_base64(log_part)
        log_part.add_header(
            'Content-Disposition',
            'attachment; filename="log.txt"',
        )
        msg.attach(log_part)

        return self.session.sendmail(self.user, self.recipients, msg.as_string())

    def send_tests_result(self, is_success, result, shell_name, log_msg):
        """Send tests result

        :param bool is_success: was tests success or not
        :param str result: test result as a string
        :param str shell_name: Shell name
        :param str log_msg: shell tests logs
        """

        success_str = 'successful' if is_success else 'unsuccessful'
        subject = 'Test was {} for "{}"'.format(success_str, shell_name)
        text = '{}\n\nTests result:\n\n{}'.format(subject, result)

        self.send_email(subject, text, log_msg)

    def send_error(self, error_msg, shell_name, log_msg):
        """Send error message

        :param str error_msg:
        :param str shell_name: Shell name
        :param str log_msg: shell tests logs
        """

        subject = 'Test failed with an error for "{}"'.format(shell_name)
        text = '{}\n\nError message:\n{}'.format(subject, error_msg)

        self.send_email(subject, text, log_msg)


class ResourceReport(object):
    def __init__(self, resource_name, device_ip, device_type, is_success, test_result):
        self.name = resource_name
        self.ip = device_ip
        self.device_type = device_type
        self.is_success = is_success
        self.test_result = test_result


class Reporting(object):
    def __init__(self, shell_name):
        self.shell_name = shell_name
        self.resources_report = []  # type: list[ResourceReport]

    @property
    def is_success(self):
        return all(report.is_success for report in self.resources_report)

    def add_resource_report(self, resource_name, device_ip, device_type, is_success, test_result):
        self.resources_report.append(
            ResourceReport(resource_name, device_ip, device_type, is_success, test_result)
        )

    def get_result(self):
        results = []

        for report in self.resources_report:
            success_str = 'successful' if report.is_success else 'unsuccessful'
            results.append(
                'Resource name: {}, IP: {}, Type: {}\n'
                'Test for device was {}\n'
                '{}'.format(
                    report.name, report.ip, report.device_type, success_str, report.test_result)
            )

        return '\n\n'.join(results)
