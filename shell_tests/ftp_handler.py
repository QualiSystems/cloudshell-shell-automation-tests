import ftplib
from io import StringIO


class FtpError(Exception):
    """Base Error"""


class FtpFileNotFoundError(FtpError):
    """File not found"""

    def __init__(self, file_name):
        self.file_name = file_name

    def __str__(self):
        return 'File not found - {}'.format(self.file_name)


class FTPHandler(object):
    def __init__(self, host, user, password, logger):
        """FTP Handler

        :param str host:
        :param str user:
        :param str password:
        :param logging.Logger logger:
        """
        self.host = host
        self.user = user
        self.password = password
        self.logger = logger

        self._session = None

    @classmethod
    def from_conf(cls, conf, logger):
        """Create FTP Handler from the config.

        :type conf: shell_tests.configs.FTPConfig
        :type logger: logging.Logger
        """
        return cls(
            conf.host,
            conf.user,
            conf.password,
            logger,
        )

    @property
    def session(self):
        if self._session is None:
            self._session = ftplib.FTP(self.host)
            self.logger.info('Connecting to FTP')
            self._session.login(self.user, self.password)
        return self._session

    def get_file(self, file_name):
        s_io = StringIO()

        self.logger.info('Reading file {} from FTP'.format(file_name))

        try:
            self.session.retrbinary('RETR {}'.format(file_name), s_io.writelines)
        except ftplib.Error as e:
            if str(e).startswith('550 No such file'):
                raise FtpFileNotFoundError(file_name)
            raise e

        text = s_io.getvalue()

        self.logger.debug('File content:\n{}'.format(text))
        return text

    def delete_file(self, file_name):
        self.logger.info('Deleting file {}'.format(file_name))

        try:
            self.session.delete(file_name)
        except ftplib.Error as e:
            if str(e).startswith('550 No such file'):
                raise FtpFileNotFoundError(file_name)
            raise e
