import tempfile
from functools import cached_property
from pathlib import Path
from typing import List
from urllib.parse import urlparse
from urllib.request import urlretrieve

from shell_tests.helpers.logger import logger


def get_file_name(url: str) -> str:
    return Path(urlparse(url).path).name


class DownloadFile:
    _downloaded_files: List["DownloadFile"] = []

    def __init__(self, path_str: str):
        self.original_path = path_str

    @cached_property
    def tmp_dir(self) -> Path:
        path = Path(tempfile.gettempdir()) / "shell_tests"
        path.mkdir(exist_ok=True)
        return path

    @staticmethod
    def _is_url(url: str) -> bool:
        return urlparse(url).scheme in ("http", "https", "ftp", "ftps", "tftp")

    @cached_property
    def path(self) -> Path:
        if not self._is_url(self.original_path):
            return Path(self.original_path)

        path = self.tmp_dir / get_file_name(self.original_path)
        logger.info(f"Downloading a file {path.name}")
        urlretrieve(self.original_path, path)
        self._downloaded_files.append(self)
        return path

    # todo add handler for deleting files before exit from the script
    @classmethod
    def remove_downloaded_files(cls):
        logger.info("Deleting downloaded files")
        for path in cls._downloaded_files:
            path.path.unlink(missing_ok=True)
