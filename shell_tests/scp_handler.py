import paramiko

class ScpError(Exception):
    """Base Error"""

class ScpFileNotFoundError(ScpError):
    """File not found"""

    def __init__(self, file_name):
        self.file_name = file_name

    def __str__(self):
        return 'File not found - {}'.format(self.file_name)


class SCPHandler(object):
    def __init__(self, host, user, password, logger):
        """SCP Handler

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
        """Create SCP Handler from the config.

        :type conf: shell_tests.configs.SCPConfig
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
            transport = paramiko.Transport(self.host)
            self.logger.info('Connecting to SCP')
            transport.connect(None, self.user, self.password)
            self._session = paramiko.SFTPClient.from_transport(transport)
        return self._session

    def get_file(self, file_name):

        self.logger.info('Reading file {} from SCP'.format(file_name))

        try:
            resp = self.session.open(file_name)
            text = resp.read()
        except Exception as e:
            if str(e).startswith('No such file'):
                raise ScpFileNotFoundError(file_name)
            raise e


        self.logger.debug('File content:\n{}'.format(text))
        return text

    def delete_file(self, file_name):
        self.logger.info('Deleting file {}'.format(file_name))

        try:
            self.session.remove(file_name)
        except Exception as e:
            if str(e).startswith('No such file'):
                raise ScpFileNotFoundError(file_name)
            raise e
