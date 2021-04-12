import re
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from shell_tests.helpers.logger import logger

LOGGING_PATTERN = re.compile(r"^cloudshell[-_]logging-", flags=re.IGNORECASE)


def gen_new_zip_with_replacement(
    zip_file: ZipFile, replacements: dict[str, bytes]
) -> bytes:
    buffer = BytesIO()
    with ZipFile(buffer, mode="w") as new_zip:
        for file_name in zip_file.namelist():
            if file_name in replacements:
                if replacements[file_name] is None:
                    continue  # do not add this file; "remove it"
                else:
                    data = replacements[file_name]
            else:
                data = zip_file.read(file_name)
            new_zip.writestr(file_name, data)
    buffer.seek(0)
    return buffer.read()


def get_new_config_and_path(zip_file: ZipFile) -> tuple[bytes, str]:
    logger.info(f"Setting log level for {zip_file.filename}")
    ext = Path(zip_file.filename).suffix
    if ext == ".zip":
        dirs = {name.split("/", 1)[0] for name in zip_file.namelist()}
        assert len(dirs) == 1
        config_path = f"{next(iter(dirs))}/cloudshell/logging/qs_config.ini"
    elif ext == ".whl":
        config_path = "cloudshell/logging/qs_config.ini"
    else:
        raise NotImplementedError(f"Extension {ext} is not supported")

    with zip_file.open(config_path) as fo:
        data = fo.read()
    data = data.replace(b"LOG_LEVEL='INFO'", b"LOG_LEVEL='DEBUG'")
    return data, config_path


def patch_dependencies(path: Path):
    msg = f"Changing log level to debug via changing dependencies {path.name}"
    logger.info(msg)
    replacements = {}
    with ZipFile(path) as dep_zip:
        for package_name in dep_zip.namelist():
            if LOGGING_PATTERN.search(package_name):
                with ZipFile(dep_zip.open(package_name)) as logging_zip:
                    config_data, config_path = get_new_config_and_path(logging_zip)
                    new_logging = gen_new_zip_with_replacement(
                        logging_zip, {config_path: config_data}
                    )
                replacements[package_name] = new_logging
        new_dependencies = gen_new_zip_with_replacement(dep_zip, replacements)

    with path.open("wb") as dep_zip_fo:
        dep_zip_fo.write(new_dependencies)
