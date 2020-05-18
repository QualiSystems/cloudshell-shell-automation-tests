import tftpy
import sys
import StringIO

class TftpError(Exception):
    """Base Error"""

class TftpFileNotFoundError(TftpError):
    """File not found"""

    def __init__(self, file_name):
        self.file_name = file_name

    def __str__(self):
        return 'File not found - {}'.format(self.file_name)

class TFTPHandler(object):
    def __init__(self, host, logger):
        """SCP Handler

        :param str host:
        :param logging.Logger logger:
        """
        self.host = host
        self.logger = logger

        self._session = None

    @classmethod
    def from_conf(cls, conf, logger):
        """Create TFTP Handler from the config.

        :type conf: shell_tests.configs.TFTPConfig
        :type logger: logging.Logger
        """
        return cls(
            conf.host,
            logger,
        )

    @property
    def session(self):
        if self._session is None:
            self._session = tftpy.TftpClient(self.host)
            #transport = paramiko.Transport((self.host))
            self.logger.info('Connecting to TFTP')
            #transport.connect(None, self.user, self.password)
            #self._session = paramiko.SFTPClient.from_transport(transport)
        return self._session

    def get_file(self, file_name):

        self.logger.info('Reading file {} from TFTP'.format(file_name))
        temp_out = StringIO.StringIO()
        sys.stdout = temp_out

        try:
            self.session.download(file_name, '-')
            sys.stdout = sys.__stdout__
            text = temp_out.getvalue()
            self.logger.debug('File content:\n{}'.format(text))
        except Exception as e:
            text = "TFTP doesn't work"
            self.logger.debug('File content:\n{}'.format(text))
            if str(e).startswith('No such file'):
                raise TftpFileNotFoundError(file_name)
            raise e

        #sys.stdout = sys.__stdout__
        #text = temp_out.getvalue()

        return text

    def delete_file(self, file_name):
        self.logger.info('Deleting file {}'.format(file_name))
        pass

        # try:
        #     self.session.remove(file_name)
        # except Exception as e:
        #     if str(e).startswith('No such file'):
        #         raise ScpFileNotFoundError(file_name)
        #     raise e