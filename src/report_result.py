import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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

    def send_email(self, subject, text):
        """Sends email

        :param str subject: email subject
        :param str text: email text
        """

        msg = MIMEMultipart()
        msg['From'] = self.user
        msg['To'] = ', '.join(self.recipients)
        msg['Subject'] = subject

        msg.attach(MIMEText(text, 'plain'))

        return self.session.sendmail(self.user, self.recipients, msg.as_string())

    @staticmethod
    def _get_shell_name(shell_path):
        return re.split(r'[\\/]', shell_path)[-1]

    def send_tests_result(self, success, result, shell_path):
        """Send tests result

        :param bool success: was tests success or not
        :param str result: test result as a string
        :param str shell_path: path to the Shell
        """

        shell_name = self._get_shell_name(shell_path)
        success_str = 'successful' if success else 'unsuccessful'
        subject = 'Test was {} for "{}"'.format(success_str, shell_name)
        text = '{}\n\nTests output:\n{}'.format(subject, result)

        self.send_email(subject, text)

    def send_error(self, error_msg, shell_path):
        """Send error message

        :param str error_msg:
        :param str shell_path: path to Shell
        """

        shell_name = self._get_shell_name(shell_path)
        subject = 'Test failed with an error for "{}"'.format(shell_name)
        text = '{}\n\nError message:\n{}'.format(subject, error_msg)

        self.send_email(subject, text)
