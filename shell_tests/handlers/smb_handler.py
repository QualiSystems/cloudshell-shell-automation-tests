import os
import re
import shutil
import socket
import zipfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Iterator, List, Union

from smb.base import NotConnectedError, SharedFile
from smb.SMBConnection import OperationFailure, SMBConnection

from shell_tests.configs import CloudShellConfig
from shell_tests.helpers.logger import logger


class SmbHandler:
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
                    self._username, self._password, self._client, self._server_name,
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

    def remove_file(self, r_file_path: str):
        self.session.deleteFiles(self._share, r_file_path)

    def get_r_file(self, r_file_path: str) -> bytes:
        buffer = BytesIO()
        self.session.retrieveFile(self._share, r_file_path, buffer)
        data = buffer.getvalue()
        buffer.close()
        return data

    def download_r_file(self, r_file_path: str, l_file_path: Union[Path, str]):
        with open(l_file_path, "wb") as file_obj:
            file_obj.write(self.get_r_file(r_file_path))

    def download_r_dir(self, r_dir_path: str, l_dir_path: Path):
        l_dir_path = Path(l_dir_path)
        for smb_file in self.ls(r_dir_path):
            new_l_file_path = l_dir_path / smb_file.filename
            if smb_file.isDirectory:
                new_l_file_path.mkdir()
                self.download_r_dir(
                    os.path.join(r_dir_path, smb_file.filename), new_l_file_path,
                )
            else:
                self.download_r_file(
                    os.path.join(r_dir_path, smb_file.filename), new_l_file_path,
                )


class CloudShellSmbHandler:
    _CS_SERVER_NAME = "User-PC"
    _CS_SHARE = "C$"
    _QS_PATH = r"Program Files (x86)\\QualiSystems\\"
    _CS_PYPI_PATH = fr"{_QS_PATH}CloudShell\\Server\\Config\\Pypi Server Repository\\"
    _CS_STANDARDS_PATH = fr"{_QS_PATH}CloudShell\\Server\\ToscaStandard\\"
    _CS_LOGS_SHELL_DIR = r"ProgramData\\QualiSystems\\logs"
    _CS_LOGS_INSTALLATION_DIR = (
        fr"{_QS_PATH}TestShell\\ExecutionServer\\Logs\\QsPythonDriverHost"
    )

    def __init__(self, conf: CloudShellConfig):
        self.conf = conf
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
        self._smb_handler.put_file_obj(r_file_path, file_obj)

    def add_dependencies_to_offline_pypi(self, file: Union[BinaryIO, Path]):
        logger.info("Putting dependecies to offline PyPI")
        with zipfile.ZipFile(file) as zip_file:
            for file_obj in map(zip_file.open, zip_file.filelist):
                package_name = file_obj.name
                self.add_file_obj_to_offline_pypi(file_obj, package_name)

    def get_file_names_from_offline_pypi(self) -> List[str]:
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

    def get_tosca_standards_file_names(self) -> List[str]:
        names = [
            standard.filename
            for standard in self._smb_handler.ls(self._CS_STANDARDS_PATH)
        ]
        logger.debug(f"Installed tosca standards: {names}")
        return names

    def add_extra_standards(self, extra_standards: List[Path]):
        installed_standards = self.get_tosca_standards_file_names()
        for standard in extra_standards:
            if standard.name not in installed_standards:
                self._add_cs_standard_file_path(standard)

    def download_logs(self, path_to_save: Path):
        logger.info("Downloading CS logs")
        if path_to_save.exists():
            shutil.rmtree(path_to_save)
        path_to_save.mkdir()

        shell_logs_path = path_to_save / "shell_logs"
        installation_logs_path = path_to_save / "installation_logs"
        shell_logs_path.mkdir()
        installation_logs_path.mkdir()

        self._smb_handler.download_r_dir(self._CS_LOGS_SHELL_DIR, shell_logs_path)
        self._smb_handler.download_r_dir(
            self._CS_LOGS_INSTALLATION_DIR, installation_logs_path
        )
        logger.debug("CS logs downloaded")
