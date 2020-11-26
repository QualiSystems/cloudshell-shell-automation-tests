from functools import cached_property

import paramiko

from shell_tests.configs import HostWithUserConfig
from shell_tests.handlers.abc_remote_file_handler import AbcRemoteFileHandler
from shell_tests.helpers.logger import logger


class ScpError(Exception):
    """Base Error."""


class ScpFileNotFoundError(ScpError):
    """File not found."""

    def __init__(self, file_name: str):
        self.file_name = file_name

    def __str__(self):
        return f"File not found - {self.file_name}"


class SCPHandler(AbcRemoteFileHandler):
    def __init__(self, conf: HostWithUserConfig):
        super().__init__(conf)
        self.conf = conf

    @cached_property
    def session(self):
        transport = paramiko.Transport(self.conf.netloc)
        logger.info("Connecting to SCP")
        transport.connect(None, self.conf.user, self.conf.password)
        return paramiko.SFTPClient.from_transport(transport)

    def _retry_on_file_not_found(self, exception: Exception) -> bool:
        return isinstance(exception, ScpFileNotFoundError)

    def _read_file(self, file_path: str) -> bytes:
        logger.info(f"Reading file {file_path} from SCP")
        try:
            resp = self.session.open(file_path)
            data = resp.read()
        except Exception as e:
            if str(e).startswith("No such file"):
                raise ScpFileNotFoundError(file_path)
            raise e
        return data

    def _delete_file(self, file_path: str):
        logger.info(f"Deleting file {file_path}")
        try:
            self.session.remove(file_path)
        except Exception as e:
            if str(e).startswith("No such file"):
                raise ScpFileNotFoundError(file_path)
            raise e
