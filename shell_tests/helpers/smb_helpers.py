from collections import Iterable
from datetime import datetime, timedelta

from smb.base import SharedFile


class FilterByLastWriteTime:
    def __init__(self, start_time: datetime):
        self._start_time = start_time

    def __call__(self, smb_file: SharedFile) -> bool:
        # time on the server could be incorrect =/
        return (
            datetime.fromtimestamp(smb_file.last_write_time) + timedelta(days=1)
            > self._start_time
        )


class FilterByFileNameInIterable:
    def __init__(self, iterable: Iterable):
        self._iterable = iterable

    def __call__(self, smb_file: SharedFile) -> bool:
        return smb_file.filename in self._iterable
