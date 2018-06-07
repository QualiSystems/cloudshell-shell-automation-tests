import ftplib

import StringIO


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

    @property
    def session(self):
        if self._session is None:
            self._session = ftplib.FTP(self.host)
            self.logger.info('Connecting to FTP')
            self._session.login(self.user, self.password)
        return self._session

    def get_file(self, file_name):
        s_io = StringIO.StringIO()

        self.logger.info('Reading file {} from FTP'.format(file_name))
        self.session.retrbinary('RETR {}'.format(file_name), s_io.writelines)
        text = s_io.getvalue()

        self.logger.debug('File content:\n{}'.format(text))
        return text

    def delete_file(self, file_name):
        self.logger.info('Deleting file {}'.format(file_name))
        self.session.delete(file_name)
