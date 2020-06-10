from functools import cached_property

import paramiko

from shell_tests.configs import SCPConfig
from shell_tests.helpers.logger import logger


class ScpError(Exception):
    """Base Error."""


class ScpFileNotFoundError(ScpError):
    """File not found."""

    def __init__(self, file_name: str):
        self.file_name = file_name

    def __str__(self):
        return f"File not found - {self.file_name}"


class SCPHandler:
    def __init__(self, conf: SCPConfig):
        self.conf = conf

    @cached_property
    def session(self):
        transport = paramiko.Transport(self.conf.host)
        logger.info("Connecting to SCP")
        transport.connect(None, self.conf.user, self.conf.password)
        return paramiko.SFTPClient.from_transport(transport)

    def read_file(self, file_name: str) -> bytes:
        logger.info(f"Reading file {file_name} from SCP")
        try:
            resp = self.session.open(file_name)
            data = resp.read()
        except Exception as e:
            if str(e).startswith("No such file"):
                raise ScpFileNotFoundError(file_name)
            raise e
        return data

    def delete_file(self, file_name: str):
        logger.info(f"Deleting file {file_name}")
        try:
            self.session.remove(file_name)
        except Exception as e:
            if str(e).startswith("No such file"):
                raise ScpFileNotFoundError(file_name)
            raise e
