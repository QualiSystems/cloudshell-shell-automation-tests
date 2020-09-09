import ftplib
from functools import cached_property
from io import BytesIO

from retrying import retry

from shell_tests.configs import FTPConfig
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


class FTPHandler:
    def __init__(self, conf: FTPConfig):
        self.conf = conf

    @cached_property
    def session(self):
        session = ftplib.FTP(self.conf.host)
        logger.info("Connecting to FTP")
        if self.conf.user and self.conf.password:
            session.login(self.conf.user, self.conf.password)
        return session

    @retry(
        stop_max_attempt_number=10,
        wait_fixed=3000,
        retry_on_exception=_retry_on_file_not_found,
    )
    def read_file(self, file_name: str) -> bytes:
        logger.info(f"Reading file {file_name} from FTP")
        b_io = BytesIO()
        try:
            self.session.retrbinary(f"RETR {file_name}", b_io.write)
        except ftplib.Error as e:
            if str(e).startswith("550 No such file"):
                raise FtpFileNotFoundError(file_name)
            raise e
        return b_io.getvalue()

    @retry(
        stop_max_attempt_number=10,
        wait_fixed=3000,
        retry_on_exception=_retry_on_file_not_found,
    )
    def delete_file(self, file_name: str):
        logger.info(f"Deleting file {file_name}")
        try:
            self.session.delete(file_name)
        except ftplib.Error as e:
            if str(e).startswith("550 No such file"):
                raise FtpFileNotFoundError(file_name)
            raise e
