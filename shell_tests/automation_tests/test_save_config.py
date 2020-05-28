import json

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseResourceServiceTestCase
from shell_tests.helpers.download_files_helper import get_file_name


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
