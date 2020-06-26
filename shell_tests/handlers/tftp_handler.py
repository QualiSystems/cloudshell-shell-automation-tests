from functools import cached_property
from io import BytesIO

import tftpy

from shell_tests.configs import TFTPConfig
from shell_tests.helpers.logger import logger


class TftpError(Exception):
    """Base Error."""


class TftpFileNotFoundError(TftpError):
    """File not found."""

    def __init__(self, file_name: str):
        self.file_name = file_name

    def __str__(self):
        return f"File not found - {self.file_name}"


class TFTPHandler:
    def __init__(self, conf: TFTPConfig):
        self.conf = conf

    @cached_property
    def session(self):
        logger.info("Connecting to TFTP")
        return tftpy.TftpClient(self.conf.host)

    def read_file(self, file_name: str) -> bytes:
        logger.info(f"Reading file {file_name} from TFTP")
        bio = BytesIO()
        try:
            self.session.download(file_name, bio)
        except Exception as e:
            if str(e).startswith("No such file"):
                raise TftpFileNotFoundError(file_name)
            raise e
        return bio.getvalue()

    def delete_file(self, file_name):
        # todo find ability to delete file after TFTP
        logger.warning(f"Deleting file {file_name}")
