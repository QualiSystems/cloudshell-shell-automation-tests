import socket

from smb.SMBConnection import SMBConnection
from smb.base import NotConnectedError


class SMB(object):
    def __init__(self, username, password, ip, server_name, logger):
        # split username if it contains a domain
        self.domain, self.username = username.split('\\') if '\\' in username else '', username
        self.password = password
        self.client = socket.gethostname()
        self.server_ip = ip
        self.server_name = server_name
        self.logger = logger
        self._session = None

    @property
    def session(self):
        if not self._session:
            self.logger.info('Creating SMB session to {}'.format(self.server_ip))
            try:
                self._session = SMBConnection(
                    self.username, self.password, self.client, self.server_name,
                )
                self._session.connect(self.server_ip)
            except NotConnectedError:
                self._session = SMBConnection(
                    self.username, self.password, self.client, self.server_name, is_direct_tcp=True,
                )
                self._session.connect(self.server_ip, 445)
        return self._session

    def ls(self, share, dir_path):
        return self.session.listPath(share, dir_path)

    def put_file(self, share, file_path, file_obj):
        self.session.storeFile(share, file_path, file_obj)

    def remove_file(self, share, file_path):
        self.session.deleteFiles(share, file_path)
