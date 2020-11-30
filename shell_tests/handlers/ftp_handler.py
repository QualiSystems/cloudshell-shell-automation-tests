import ftplib
from functools import cached_property
from io import BytesIO

from retrying import retry

from shell_tests.configs import HostWithUserConfig
from shell_tests.handlers.abc_remote_file_handler import AbcRemoteFileHandler
from shell_tests.helpers.logger import logger


class FtpError(Exception):
    """Base Error."""


class FtpFileNotFoundError(FtpError):
    """File not found."""

    def __init__(self, file_name):
        self.file_name = file_name

    def __str__(self):
        return f"File not found - {self.file_name}"


def _retry_on_file_not_found(exception: Exception) -> bool:
    return isinstance(exception, FtpFileNotFoundError)


class FTPHandler(AbcRemoteFileHandler):
    RETRY_STOP_MAX_ATTEMPT_NUM = 10
    RETRY_WAIT_FIXED = 3000
    IS_RETRY_FUNC = _retry_on_file_not_found

    def __init__(self, conf: HostWithUserConfig):
        super().__init__(conf)
        self.conf = conf

    @cached_property
    def session(self):
        session = ftplib.FTP(self.conf.host)
        logger.info("Connecting to FTP")
        if self.conf.user and self.conf.password:
            session.login(self.conf.user, self.conf.password)
        return session

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=IS_RETRY_FUNC,
    )
    def _read_file(self, file_path: str) -> bytes:
        logger.info(f"Reading file {file_path} from FTP")
        b_io = BytesIO()
        try:
            self.session.retrbinary(f"RETR {file_path}", b_io.write)
        except ftplib.Error as e:
            if str(e).startswith("550 No such file"):
                raise FtpFileNotFoundError(file_path)
            raise e
        return b_io.getvalue()

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=IS_RETRY_FUNC,
    )
    def _delete_file(self, file_path: str):
        logger.info(f"Deleting file {file_path}")
        try:
            self.session.delete(file_path)
        except ftplib.Error as e:
            if str(e).startswith("550 No such file"):
                raise FtpFileNotFoundError(file_path)
            raise e
