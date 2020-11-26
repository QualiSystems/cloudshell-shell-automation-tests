from functools import cached_property
from io import BytesIO

import tftpy

from shell_tests.handlers.abc_remote_file_handler import AbcRemoteFileHandler
from shell_tests.helpers.logger import logger


class TftpError(Exception):
    """Base Error."""


class TftpFileNotFoundError(TftpError):
    """File not found."""

    def __init__(self, file_name: str):
        self.file_name = file_name

    def __str__(self):
        return f"File not found - {self.file_name}"


def _retry_on_file_not_found(exception: Exception) -> bool:
    return isinstance(exception, TftpFileNotFoundError)


class TFTPHandler(AbcRemoteFileHandler):
    @cached_property
    def session(self):
        logger.info("Connecting to TFTP")
        return tftpy.TftpClient(self.conf.host)

    def _retry_on_file_not_found(self, exception: Exception) -> bool:
        return isinstance(exception, TftpFileNotFoundError)

    def _read_file(self, file_path: str) -> bytes:
        logger.info(f"Reading file {file_path} from TFTP")
        bio = BytesIO()
        try:
            self.session.download(file_path, bio)
        except Exception as e:
            if str(e).startswith("No such file"):
                raise TftpFileNotFoundError(file_path)
            raise e
        return bio.getvalue()

    def _delete_file(self, file_path: str):
        # todo find ability to delete file after TFTP
        logger.warning("We cannot delete files from TFTP server.")
        logger.info(f"Trying to delete {file_path}")
