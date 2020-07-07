import json
from typing import Type

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import (
    BaseResourceServiceTestCase,
    OptionalTestCase,
)
from shell_tests.helpers.download_files_helper import get_file_name
from shell_tests.helpers.handler_storage import HandlerStorage


class TestSaveConfig(BaseResourceServiceTestCase):
    @property
    def ftp_path(self):
        ftp = self.handler_storage.conf.ftp_conf
        return f"ftp://{ftp.user}:{ftp.password}@{ftp.host}"

    def test_save_running_config(self):
        file_name = self.handler.save(self.ftp_path, "running")
        self.assertTrue(self.handler_storage.ftp_handler.read_file(file_name))
        self.handler_storage.ftp_handler.delete_file(file_name)

    def test_save_startup_config(self):
        file_name = self.handler.save(self.ftp_path, "startup")
        self.assertTrue(self.handler_storage.ftp_handler.read_file(file_name))
        self.handler_storage.ftp_handler.delete_file(file_name)

    def test_orchestration_save_shallow(self):
        custom_params = {"custom_params": {"folder_path": self.ftp_path}}
        saved_artifact_info = self.handler.orchestration_save(
            "shallow", json.dumps(custom_params)
        )
        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)["saved_artifacts_info"][
            "saved_artifact"
        ]["identifier"]
        file_name = get_file_name(path)
        self.assertTrue(self.handler_storage.ftp_handler.read_file(file_name))
        self.handler_storage.ftp_handler.delete_file(file_name)

    def test_orchestration_save_deep(self):
        custom_params = {"custom_params": {"folder_path": self.ftp_path}}
        saved_artifact_info = self.handler.orchestration_save(
            "deep", json.dumps(custom_params)
        )
        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)["saved_artifacts_info"][
            "saved_artifact"
        ]["identifier"]
        file_name = get_file_name(path)
        self.assertTrue(self.handler_storage.ftp_handler.read_file(file_name))
        self.handler_storage.ftp_handler.delete_file(file_name)


class OptionalTestSaveFtpConfig(OptionalTestCase):
    @staticmethod
    def test_case() -> Type[BaseResourceServiceTestCase]:
        return TestSaveConfig

    @staticmethod
    def is_suitable(handler, handler_storage: HandlerStorage) -> bool:
        return handler_storage.conf.ftp_conf is not None


class TestSaveConfigFromScp(BaseResourceServiceTestCase):
    @property
    def scp_path(self):
        scp = self.handler_storage.conf.scp_conf
        return f"scp://{scp.user}:{scp.password}@{scp.host}"

    def test_save_running_config(self):
        file_name = self.handler.save(self.scp_path, "running")
        self.assertTrue(self.handler_storage.scp_handler.read_file(file_name))
        self.handler_storage.scp_handler.delete_file(file_name)

    def test_save_startup_config(self):
        file_name = self.handler.save(self.scp_path, "startup")
        self.assertTrue(self.handler_storage.scp_handler.read_file(file_name))
        self.handler_storage.scp_handler.delete_file(file_name)

    def test_orchestration_save_shallow(self):
        custom_params = {"custom_params": {"folder_path": self.scp_path}}

        saved_artifact_info = self.handler.orchestration_save(
            "shallow", json.dumps(custom_params)
        )

        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)["saved_artifacts_info"][
            "saved_artifact"
        ]["identifier"]
        file_name = get_file_name(path)

        self.assertTrue(self.handler_storage.scp_handler.read_file(file_name))
        self.handler_storage.scp_handler.delete_file(file_name)

    def test_orchestration_save_deep(self):
        custom_params = {"custom_params": {"folder_path": self.scp_path}}

        saved_artifact_info = self.handler.orchestration_save(
            "deep", json.dumps(custom_params)
        )

        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)["saved_artifacts_info"][
            "saved_artifact"
        ]["identifier"]
        file_name = get_file_name(path)

        self.assertTrue(self.handler_storage.scp_handler.read_file(file_name))
        self.handler_storage.scp_handler.delete_file(file_name)


class OptionalTestSaveScpConfig(OptionalTestCase):
    @staticmethod
    def test_case() -> Type[BaseResourceServiceTestCase]:
        return TestSaveConfigFromScp

    @staticmethod
    def is_suitable(handler, handler_storage: HandlerStorage) -> bool:
        return handler_storage.conf.scp_conf is not None


class TestSaveConfigFromTftp(BaseResourceServiceTestCase):
    @property
    def tftp_path(self):
        return f"tftp://{self.handler_storage.conf.tftp_conf.host}"

    def test_save_running_config(self):
        file_name = self.handler.save(self.tftp_path, "running")
        self.assertTrue(self.handler_storage.tftp_handler.read_file(file_name))
        self.handler_storage.tftp_handler.delete_file(file_name)

    def test_save_startup_config(self):
        file_name = self.handler.save(self.tftp_path, "startup")
        self.assertTrue(self.handler_storage.tftp_handler.read_file(file_name))
        self.handler_storage.tftp_handler.delete_file(file_name)

    def test_orchestration_save_shallow(self):
        custom_params = {"custom_params": {"folder_path": self.tftp_path}}

        saved_artifact_info = self.handler.orchestration_save(
            "shallow", json.dumps(custom_params)
        )

        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)["saved_artifacts_info"][
            "saved_artifact"
        ]["identifier"]
        file_name = get_file_name(path)

        self.assertTrue(self.handler_storage.tftp_handler.read_file(file_name))
        self.handler_storage.tftp_handler.delete_file(file_name)

    def test_orchestration_save_deep(self):
        custom_params = {"custom_params": {"folder_path": self.tftp_path}}

        saved_artifact_info = self.handler.orchestration_save(
            "deep", json.dumps(custom_params)
        )

        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)["saved_artifacts_info"][
            "saved_artifact"
        ]["identifier"]
        file_name = get_file_name(path)

        self.assertTrue(self.handler_storage.tftp_handler.read_file(file_name))
        self.handler_storage.tftp_handler.delete_file(file_name)


class OptionalTestSaveTftpConfig(OptionalTestCase):
    @staticmethod
    def test_case() -> Type[BaseResourceServiceTestCase]:
        return TestSaveConfigFromTftp

    @staticmethod
    def is_suitable(handler, handler_storage: HandlerStorage) -> bool:
        return handler_storage.conf.tftp_conf is not None


class TestSaveConfigWithoutDevice(TestSaveConfig):
    def test_save_running_config(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.save(self.ftp_path, "running")

    def test_save_startup_config(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.save(self.ftp_path, "startup")

    def test_orchestration_save_shallow(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.orchestration_save("shallow")

    def test_orchestration_save_deep(self):
        with self.assertRaisesRegexp(CloudShellAPIError, r"SessionManagerException"):
            self.handler.orchestration_save("deep")


class TestSaveConfigFromTemplate(BaseResourceServiceTestCase):
    def test_save_running_config(self):
        self.handler.save("ftp://", "running")

    def test_orchestration_save_deep(self):
        custom_params = {"custom_params": {"folder_path": "ftp://"}}
        self.handler.orchestration_save("deep", json.dumps(custom_params))

    def test_orchestration_save_shallow(self):
        custom_params = {"custom_params": {"folder_path": "ftp://"}}
        self.handler.orchestration_save("shallow", json.dumps(custom_params))
