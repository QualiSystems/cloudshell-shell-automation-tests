from typing import Tuple


def str_version_to_tuple(version: str) -> Tuple[int]:
    return tuple(map(int, version.split(".")))
