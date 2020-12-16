def str_version_to_tuple(version: str) -> tuple[int]:
    return tuple(map(int, version.split(".")))
