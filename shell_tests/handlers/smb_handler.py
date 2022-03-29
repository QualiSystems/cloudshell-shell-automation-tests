import os
import re
import shutil
import socket
import zipfile
from collections.abc import Callable, Iterator
from contextlib import suppress
from datetime import datetime
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import BinaryIO, Union

from retrying import retry
from smb.base import NotConnectedError, NotReadyError, SharedFile, SMBTimeout
from smb.SMBConnection import OperationFailure, SMBConnection

from shell_tests.configs import CloudShellConfig
from shell_tests.helpers.logger import logger
from shell_tests.helpers.smb_helpers import (
    FilterByFileNameInIterable,
    FilterByLastWriteTime,
)


def _retry_on(exception: Exception) -> bool:
    return isinstance(exception, (NotReadyError, SMBTimeout))


class SmbHandler:
    RETRY_STOP_MAX_ATTEMPT_NUM = 10
    RETRY_WAIT_FIXED = 3000
    RETRY_FUNC = _retry_on

    def __init__(
        self, username: str, password: str, ip: str, server_name: str, share: str
    ):
        # split username if it contains a domain
        self._domain, self._username = (
            username.split("\\") if "\\" in username else "",
            username,
        )
        self._password = password
        self._client = socket.gethostname()
        self._server_ip = ip
        self._server_name = server_name
        self._share = share
        self._session = None

    @property
    def session(self) -> SMBConnection:
        if self._session:
            try:
                self._session.echo(b"test connection")
            except Exception as e:
                logger.debug(f"Session error, type - {type(e)}")
                self._session = None

        if not self._session:
            logger.debug(f"Creating SMB session to {self._server_ip}")
            try:
                self._session = SMBConnection(
                    self._username, self._password, self._client, self._server_name
                )
                self._session.connect(self._server_ip)
            except NotConnectedError:
                self._session = SMBConnection(
                    self._username,
                    self._password,
                    self._client,
                    self._server_name,
                    is_direct_tcp=True,
                )
                self._session.connect(self._server_ip, 445)
            logger.debug("SMB session created")
        return self._session

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=RETRY_FUNC,
    )
    def ls(self, r_dir_path: str) -> Iterator[SharedFile]:
        try:
            smb_files = self.session.listPath(self._share, r_dir_path)
        except OperationFailure as e:
            if "Unable to open directory" not in e.message:
                raise
            smb_files = []

        return filter(lambda smb_file: smb_file.filename not in (".", ".."), smb_files)

    @staticmethod
    def get_dir_path(path: str) -> str:
        try:
            dir_path = re.search(r"^(.*)[\\/](.*?)$", path).group(1)
        except AttributeError:
            dir_path = ""
        return dir_path

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=RETRY_FUNC,
    )
    def create_dir(self, r_dir_path: str, parents: bool = True):
        try:
            logger.debug(f"Creating directory {r_dir_path}")
            self.session.createDirectory(self._share, r_dir_path)
        except OperationFailure as e:
            if parents and "Create failed" in str(e):
                r_parent_dir = self.get_dir_path(r_dir_path)
                self.create_dir(r_parent_dir, parents)
                self.session.createDirectory(self._share, r_dir_path)
            else:
                raise e

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=RETRY_FUNC,
    )
    def put_file_obj(
        self, r_file_path: str, file_obj: BinaryIO, create_dirs: bool = False
    ):
        try:
            self.session.storeFile(self._share, r_file_path, file_obj)
        except OperationFailure as e:
            if create_dirs and "Unable to open file" in str(e):
                r_dir_path = self.get_dir_path(r_file_path)
                self.create_dir(r_dir_path, parents=True)
                self.session.storeFile(self._share, r_file_path, file_obj)
            else:
                raise e

    def put_file_path(
        self, r_file_path: str, l_file_path: Union[Path, str], create_dirs: bool = False
    ):
        with open(l_file_path, "rb") as file_obj:
            self.put_file_obj(r_file_path, file_obj, create_dirs)

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=RETRY_FUNC,
    )
    def remove_file(self, r_file_path: str):
        self.session.deleteFiles(self._share, r_file_path)

    @retry(
        stop_max_attempt_number=RETRY_STOP_MAX_ATTEMPT_NUM,
        wait_fixed=RETRY_WAIT_FIXED,
        retry_on_exception=RETRY_FUNC,
    )
    def get_r_file(self, r_file_path: str) -> bytes:
        buffer = BytesIO()
        self.session.retrieveFile(self._share, r_file_path, buffer)
        data = buffer.getvalue()
        buffer.close()
        return data

    def download_r_file(self, r_file_path: str, l_file_path: Union[Path, str]):
        with open(l_file_path, "wb") as file_obj:
            file_obj.write(self.get_r_file(r_file_path))

    def download_r_dir(
        self,
        r_dir_path: str,
        l_dir_path: Path,
        filter_fn: Callable[[SharedFile], bool] = None,
    ):
        l_dir_path = Path(l_dir_path)
        for smb_file in self.ls(r_dir_path):
            if not filter_fn or filter_fn(smb_file):
                new_l_file_path = l_dir_path / smb_file.filename
                r_file_path = os.path.join(r_dir_path, smb_file.filename)
                if smb_file.isDirectory:
                    new_l_file_path.mkdir()
                    self.download_r_dir(r_file_path, new_l_file_path)
                else:
                    self.download_r_file(r_file_path, new_l_file_path)


class CloudShellSmbHandler:
    _CS_SERVER_NAME = "User-PC"
    _CS_SHARE = "C$"
    _QS_PATH = r"Program Files (x86)\\QualiSystems\\"
    _CS_PYPI_PATH = rf"{_QS_PATH}CloudShell\\Server\\Config\\Pypi Server Repository\\"
    _CS_STANDARDS_PATH = rf"{_QS_PATH}CloudShell\\Server\\ToscaStandard\\"
    _CS_LOGS_SHELL_DIR = r"ProgramData\\QualiSystems\\logs"
    _CS_LOGS_AUTOLOAD_DIR = rf"{_CS_LOGS_SHELL_DIR}\\inventory"
    _CS_LOGS_INSTALLATION_DIR = (
        rf"{_QS_PATH}TestShell\\ExecutionServer\\Logs\\QsPythonDriverHost"
    )
    _VENV_DIR = r"ProgramData\QualiSystems\venv"
    _QS_CONFIG_PATH = (
        rf"{_VENV_DIR}\{{}}\Lib\site-packages\cloudshell\logging\qs_config.ini"
    )

    def __init__(self, conf: CloudShellConfig):
        self.conf = conf
        self._lock = Lock()
        self._smb_handler = SmbHandler(
            conf.os_user,
            conf.os_password,
            conf.host,
            self._CS_SERVER_NAME,
            self._CS_SHARE,
        )

    def add_file_obj_to_offline_pypi(self, file_obj: BinaryIO, file_name: str):
        r_file_path = f"{self._CS_PYPI_PATH}{file_name}"
        logger.debug(f"Adding a file {file_name} to offline PyPI")
        with self._lock:
            self._smb_handler.put_file_obj(r_file_path, file_obj)

    def add_dependencies_to_offline_pypi(self, file: Union[BinaryIO, Path]):
        logger.info("Putting dependencies to offline PyPI")
        with zipfile.ZipFile(file) as zip_file:
            for file_obj in map(zip_file.open, zip_file.filelist):
                package_name = file_obj.name
                self.add_file_obj_to_offline_pypi(file_obj, package_name)

    def get_file_names_from_offline_pypi(self) -> list[str]:
        logger.debug("Getting packages names from offline PyPI")
        excluded = (".", "..", "PlaceHolder.txt")
        names = [
            f.filename
            for f in self._smb_handler.ls(self._CS_PYPI_PATH)
            if f.filename not in excluded
        ]
        logger.debug(f"Got packages names {names}")
        return names

    def remove_file_from_offline_pypi(self, filename: str):
        file_path = f"{self._CS_PYPI_PATH}{filename}"
        logger.debug(f"Removing a file {filename} from offline PyPI")
        self._smb_handler.remove_file(file_path)

    def clear_offline_pypi(self):
        for package_name in self.get_file_names_from_offline_pypi():
            self.remove_file_from_offline_pypi(package_name)

    def _add_cs_standard_file_path(self, standard_path: Path):
        r_file_path = f"{self._CS_STANDARDS_PATH}{standard_path.name}"
        logger.warning(f"Adding a tosca standard {standard_path.name} to the CS")
        self._smb_handler.put_file_path(r_file_path, standard_path)

    def get_tosca_standards_file_names(self) -> list[str]:
        names = [
            standard.filename
            for standard in self._smb_handler.ls(self._CS_STANDARDS_PATH)
        ]
        logger.debug(f"Installed tosca standards: {names}")
        return names

    def add_extra_standards(self, extra_standards: list[Path]):
        installed_standards = self.get_tosca_standards_file_names()
        for standard in extra_standards:
            if standard.name not in installed_standards:
                self._add_cs_standard_file_path(standard)

    def download_logs(
        self, path_to_save: Path, start_time: datetime, reservation_ids: set[str]
    ):
        logger.info("Downloading CS logs")
        try:
            with suppress(FileNotFoundError):
                shutil.rmtree(path_to_save)
            path_to_save.mkdir()

            shell_logs_path = path_to_save / "shell_logs"
            installation_logs_path = path_to_save / "installation_logs"
            autoload_logs_path = shell_logs_path / "inventory"
            shell_logs_path.mkdir()
            installation_logs_path.mkdir()
            autoload_logs_path.mkdir()

            self._smb_handler.download_r_dir(
                self._CS_LOGS_INSTALLATION_DIR,
                installation_logs_path,
                FilterByLastWriteTime(start_time),
            )
            self._smb_handler.download_r_dir(
                self._CS_LOGS_SHELL_DIR,
                shell_logs_path,
                FilterByFileNameInIterable(reservation_ids),
            )
            self._smb_handler.download_r_dir(
                self._CS_LOGS_AUTOLOAD_DIR,
                autoload_logs_path,
                FilterByLastWriteTime(start_time),
            )
        except Exception as e:
            if "path not found" in str(e).lower():
                logger.info("Cannot find log dir")
            else:
                logger.warning(f"Cannot download logs, error: {e}")
        logger.debug("CS logs downloaded")

    def get_venv_names(self) -> list[str]:
        return [venv.filename for venv in self._smb_handler.ls(self._VENV_DIR)]

    def get_qs_config(self, venv_name: str) -> bytes:
        return self._smb_handler.get_r_file(self._QS_CONFIG_PATH.format(venv_name))

    def put_qs_config(self, venv_name: str, config: bytes):
        self._smb_handler.put_file_obj(
            self._QS_CONFIG_PATH.format(venv_name), BytesIO(config)
        )
