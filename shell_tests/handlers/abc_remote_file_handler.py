from abc import ABC, abstractmethod

from retrying import retry

from shell_tests.configs import HostConfig


class AbcRemoteFileHandler(ABC):
    RETRY_STOP_MAX_ATTEMPT_NUM = 10
    RETRY_WAIT_FIXED = 3000

    def __init__(self, conf: HostConfig):
        self.conf = conf

    @abstractmethod
    @property
    def session(self):
        raise NotImplementedError()

    @abstractmethod
    def _retry_on_file_not_found(self, exception: Exception) -> bool:
        raise NotImplementedError()

    def _get_file_path(self, file_name: str) -> str:
        return f"{self.conf.path}/{file_name}"

    @abstractmethod
    def _read_file(self, file_path: str) -> bytes:
        raise NotImplementedError()

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=_retry_on_file_not_found,
    )
    def read_file(self, file_name: str) -> bytes:
        file_path = self._get_file_path(file_name)
        return self._read_file(file_path)

    @abstractmethod
    def _delete_file(self, file_path: str):
        raise NotImplementedError()

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=_retry_on_file_not_found,
    )
    def delete_file(self, file_name: str):
        file_path = self._get_file_path(file_name)
        return self._delete_file(file_path)
