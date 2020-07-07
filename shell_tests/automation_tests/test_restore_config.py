import json
from typing import Type

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import (
    BaseResourceServiceTestCase,
    OptionalTestCase,
)
from shell_tests.helpers.download_files_helper import get_file_name
from shell_tests.helpers.handler_storage import HandlerStorage


class TestRestoreConfig(BaseResourceServiceTestCase):
    @property
    def ftp_path(self):
        ftp = self.handler_storage.conf.ftp_conf
        return f"ftp://{ftp.user}:{ftp.password}@{ftp.host}"

    def test_restore_running_config_append(self):
        file_name = self.handler.save(self.ftp_path, "running")
        config_file_path = f"{self.ftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "running", "append")
        finally:
            self.handler_storage.ftp_handler.delete_file(file_name)

    def test_restore_startup_config_append(self):
        file_name = self.handler.save(self.ftp_path, "startup")
        config_file_path = f"{self.ftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "startup", "append")
        finally:
            self.handler_storage.ftp_handler.delete_file(file_name)

    def test_restore_running_config_override(self):
        file_name = self.handler.save(self.ftp_path, "running")
        config_file_path = f"{self.ftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "running", "override")
        finally:
            self.handler_storage.ftp_handler.delete_file(file_name)

    def test_restore_startup_config_override(self):
        file_name = self.handler.save(self.ftp_path, "startup")
        config_file_path = f"{self.ftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "startup", "override")
        finally:
            self.handler_storage.ftp_handler.delete_file(file_name)

    def test_orchestration_restore(self):
        custom_params = {"custom_params": {"folder_path": self.ftp_path}}
        saved_artifact_info = self.handler.orchestration_save(
            "shallow", json.dumps(custom_params)
        )
        try:
            self.handler.orchestration_restore(
                saved_artifact_info, "",
            )
        finally:
            path = json.loads(saved_artifact_info)["saved_artifacts_info"][
                "saved_artifact"
            ]["identifier"]
            file_name = get_file_name(path)
            self.handler_storage.ftp_handler.delete_file(file_name)


class OptionalTestRestoreFtpConfig(OptionalTestCase):
    @staticmethod
    def test_case() -> Type[BaseResourceServiceTestCase]:
        return TestRestoreConfig

    @staticmethod
    def is_suitable(handler, handler_storage: HandlerStorage) -> bool:
        return handler_storage.conf.ftp_conf is not None


class TestRestoreConfigFromScp(BaseResourceServiceTestCase):
    @property
    def scp_path(self):
        scp = self.handler_storage.conf.scp_conf
        return f"scp://{scp.user}:{scp.password}@{scp.host}"

    def test_restore_running_config_append(self):
        file_name = self.handler.save(self.scp_path, "running")
        config_file_path = f"{self.scp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "running", "append")
        finally:
            self.handler_storage.scp_handler.delete_file(file_name)

    def test_restore_startup_config_append(self):
        file_name = self.handler.save(self.scp_path, "startup")
        config_file_path = f"{self.scp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "startup", "append")
        finally:
            self.handler_storage.scp_handler.delete_file(file_name)

    def test_restore_running_config_override(self):
        file_name = self.handler.save(self.scp_path, "running")
        config_file_path = f"{self.scp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "running", "override")
        finally:
            self.handler_storage.scp_handler.delete_file(file_name)

    def test_restore_startup_config_override(self):
        file_name = self.handler.save(self.scp_path, "startup")
        config_file_path = f"{self.scp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "startup", "override")
        finally:
            self.handler_storage.scp_handler.delete_file(file_name)

    def test_orchestration_restore(self):
        custom_params = {"custom_params": {"folder_path": self.scp_path}}
        saved_artifact_info = self.handler.orchestration_save(
            "shallow", json.dumps(custom_params)
        )
        try:
            self.handler.orchestration_restore(
                saved_artifact_info, "",
            )
        finally:
            path = json.loads(saved_artifact_info)["saved_artifacts_info"][
                "saved_artifact"
            ]["identifier"]
            file_name = get_file_name(path)
            self.handler_storage.scp_handler.delete_file(file_name)


class OptionalTestRestoreScpConfig(OptionalTestCase):
    @staticmethod
    def test_case() -> Type[BaseResourceServiceTestCase]:
        return TestRestoreConfigFromScp

    @staticmethod
    def is_suitable(handler, handler_storage: HandlerStorage) -> bool:
        return handler_storage.conf.scp_conf is not None


class TestRestoreConfigFromTftp(BaseResourceServiceTestCase):
    @property
    def tftp_path(self):
        return f"tftp://{self.handler_storage.conf.tftp_conf.host}"

    def test_restore_running_config_append(self):
        file_name = self.handler.save(self.tftp_path, "running")
        config_file_path = f"{self.tftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "running", "append")
        finally:
            self.handler_storage.tftp_handler.delete_file(file_name)

    def test_restore_startup_config_append(self):
        file_name = self.handler.save(self.tftp_path, "startup")
        config_file_path = f"{self.tftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "startup", "append")
        finally:
            self.handler_storage.tftp_handler.delete_file(file_name)

    def test_restore_running_config_override(self):
        file_name = self.handler.save(self.tftp_path, "running")
        config_file_path = f"{self.tftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "running", "override")
        finally:
            self.handler_storage.tftp_handler.delete_file(file_name)

    def test_restore_startup_config_override(self):
        file_name = self.handler.save(self.tftp_path, "startup")
        config_file_path = f"{self.tftp_path}/{file_name}"
        try:
            self.handler.restore(config_file_path, "startup", "override")
        finally:
            self.handler_storage.tftp_handler.delete_file(file_name)

    def test_orchestration_restore(self):
        custom_params = {"custom_params": {"folder_path": self.tftp_path}}
        saved_artifact_info = self.handler.orchestration_save(
            "shallow", json.dumps(custom_params)
        )
        try:
            self.handler.orchestration_restore(
                saved_artifact_info, "",
            )
        finally:
            path = json.loads(saved_artifact_info)["saved_artifacts_info"][
                "saved_artifact"
            ]["identifier"]
            file_name = get_file_name(path)
            self.handler_storage.tftp_handler.delete_file(file_name)


class OptionalTestRestoreTftpConfig(OptionalTestCase):
    @staticmethod
    def test_case() -> Type[BaseResourceServiceTestCase]:
        return TestRestoreConfigFromTftp

    @staticmethod
    def is_suitable(handler, handler_storage: HandlerStorage) -> bool:
        return handler_storage.conf.tftp_conf is not None


class TestRestoreConfigWithoutDevice(TestRestoreConfig):
    FTP_PATH = "ftp://localhost/test_conf"

    def test_restore_running_config_append(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.restore(self.FTP_PATH, "running", "append")

    def test_restore_startup_config_append(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.restore(self.FTP_PATH, "startup", "append")

    def test_restore_running_config_override(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.restore(self.FTP_PATH, "running", "override")

    def test_restore_startup_config_override(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.restore(self.FTP_PATH, "startup", "override")

    def test_orchestration_restore(self):
        saved_artifact_info = {
            "saved_artifacts_info": {
                "saved_artifact": {
                    "artifact_type": "local",
                    "identifier": "/device-running-130618-155327",
                },
                "resource_name": self.handler.name,
                "restore_rules": {"requires_same_resource": True},
                "created_date": "2018-06-13T15:53:34.075000",
            }
        }
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.orchestration_restore(json.dumps(saved_artifact_info))


class TestRestoreConfigFromTemplate(BaseResourceServiceTestCase):
    def test_restore_running_config_append(self):
        self.handler.restore("ftp://", "running", "override")

    def test_orchestration_restore(self):
        saved_artifact_info = {
            "saved_artifacts_info": {
                "saved_artifact": {
                    "artifact_type": "local",
                    "identifier": "/device-running-130618-155327",
                },
                "resource_name": "resource_name",
                "restore_rules": {"requires_same_resource": True},
                "created_date": "2018-06-13T15:53:34.075000",
            }
        }

        self.handler.orchestration_restore(json.dumps(saved_artifact_info))
