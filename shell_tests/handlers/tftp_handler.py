from functools import cached_property
from io import BytesIO

import tftpy
from retrying import retry

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
    RETRY_STOP_MAX_ATTEMPT_NUM = 10
    RETRY_WAIT_FIXED = 3000
    IS_RETRY_FUNC = _retry_on_file_not_found

    @cached_property
    def session(self):
        logger.info("Connecting to TFTP")
        return tftpy.TftpClient(self.conf.host)

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=IS_RETRY_FUNC,
    )
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

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=IS_RETRY_FUNC,
    )
    def _delete_file(self, file_path: str):
        # todo find ability to delete file after TFTP
        logger.warning("We cannot delete files from TFTP server.")
