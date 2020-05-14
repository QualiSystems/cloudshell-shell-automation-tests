import os
import re
import socket

from smb.SMBConnection import SMBConnection, OperationFailure
from smb.base import NotConnectedError


class SMB(object):
    def __init__(self, username, password, ip, server_name, logger):
        """SMB Handler.

        :type username: str
        :type password: str
        :type ip: str
        :type server_name: str
        :type logger: logging.Logger
        """
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
        if self._session:
            try:
                self._session.echo('test connection')
            except Exception as e:
                self.logger.debug('Session error, type - {}'.format(type(e)))
                self._session = None

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
            self.logger.debug('SMB session created')
        return self._session

    def ls(self, share, dir_path):
        try:
            smb_files = self.session.listPath(share, dir_path)
        except OperationFailure as e:
            if 'Unable to open directory' not in e.message:
                raise
            smb_files = []

        return filter(lambda smb_file: smb_file.filename not in ('.', '..'), smb_files)

    @staticmethod
    def get_dir_path(path):
        try:
            dir_path = re.search(r'^(.*)[\\/](.*?)$', path).group(1)
        except AttributeError:
            dir_path = ''
        return dir_path

    def create_dir(self, share, dir_path, parents=True):
        try:
            self.logger.debug('Creating directory {}'.format(dir_path))
            self.session.createDirectory(share, dir_path)
        except OperationFailure as e:
            if parents and 'Create failed' in str(e):
                parent_dir = self.get_dir_path(dir_path)
                self.create_dir(share, parent_dir, parents)
                self.session.createDirectory(share, dir_path)
                return

            raise e

    def put_file(self, share, file_path, file_obj, force=False):
        try:
            self.session.storeFile(share, file_path, file_obj)
        except OperationFailure as e:
            if force and 'Unable to open file' in str(e):
                dir_path = self.get_dir_path(file_path)
                self.create_dir(share, dir_path, parents=True)
                self.session.storeFile(share, file_path, file_obj)
                return

            raise e

    def remove_file(self, share, file_path):
        self.session.deleteFiles(share, file_path)

    def download_file(self, share, file_path, path_to_save):
        with open(path_to_save, 'wb') as file_obj:
            self.session.retrieveFile(share, file_path, file_obj)

    def download_dir(self, share, r_dir_path, l_dir_path):
        for smb_file in self.ls(share, r_dir_path):
            if smb_file.isDirectory:
                new_dir_path = os.path.join(l_dir_path, smb_file.filename)
                os.mkdir(new_dir_path)
                self.download_dir(
                    share,
                    os.path.join(r_dir_path, smb_file.filename),
                    new_dir_path,
                )
            else:
                file_path = os.path.join(l_dir_path, smb_file.filename)
                self.download_file(
                    share,
                    os.path.join(r_dir_path, smb_file.filename),
                    file_path,
                )
