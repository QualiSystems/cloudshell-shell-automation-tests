from abc import ABC, abstractmethod

from shell_tests.configs import HostConfig


class AbcRemoteFileHandler(ABC):
    def __init__(self, conf: HostConfig):
        self.conf = conf

    @property
    @abstractmethod
    def session(self):
        raise NotImplementedError()

    def _get_file_path(self, file_name: str) -> str:
        if self.conf.path:
            file_path = f"{self.conf.path}/{file_name}"
        else:
            file_path = file_name
        return file_path

    @abstractmethod
    def _read_file(self, file_path: str) -> bytes:
        raise NotImplementedError()

    def read_file(self, file_name: str) -> bytes:
        file_path = self._get_file_path(file_name)
        return self._read_file(file_path)

    @abstractmethod
    def _delete_file(self, file_path: str):
        raise NotImplementedError()

    def delete_file(self, file_name: str):
        file_path = self._get_file_path(file_name)
        return self._delete_file(file_path)
