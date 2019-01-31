import json

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.helpers import get_file_name_from_url


class TestSaveConfig(BaseTestCase):

    @property
    def ftp_path(self):
        return 'ftp://{0.user}:{0.password}@{0.host}'.format(self.sandbox_handler.ftp_handler)

    def test_save_running_config(self):
        file_name = self.resource_handler.save(self.ftp_path, 'running')
        self.assertTrue(
            self.sandbox_handler.ftp_handler.get_file(file_name),
        )
        self.sandbox_handler.ftp_handler.delete_file(file_name)

    def test_save_startup_config(self):
        file_name = self.resource_handler.save(self.ftp_path, 'startup')
        self.assertTrue(
            self.sandbox_handler.ftp_handler.get_file(file_name),
        )
        self.sandbox_handler.ftp_handler.delete_file(file_name)

    def test_orchestration_save_shallow(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.ftp_path,
            }
        }

        saved_artifact_info = self.resource_handler.orchestration_save(
            'shallow', json.dumps(custom_params))

        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)['saved_artifacts_info'][
            'saved_artifact']['identifier']
        file_name = get_file_name_from_url(path)

        self.assertTrue(self.sandbox_handler.ftp_handler.get_file(file_name))
        self.sandbox_handler.ftp_handler.delete_file(file_name)

    def test_orchestration_save_deep(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.ftp_path,
            }
        }

        saved_artifact_info = self.resource_handler.orchestration_save(
            'deep', json.dumps(custom_params))

        self.assertTrue(saved_artifact_info)
        path = json.loads(saved_artifact_info)['saved_artifacts_info'][
            'saved_artifact']['identifier']
        file_name = get_file_name_from_url(path)

        self.assertTrue(self.sandbox_handler.ftp_handler.get_file(file_name))
        self.sandbox_handler.ftp_handler.delete_file(file_name)


class TestSaveConfigWithoutDevice(TestSaveConfig):
    def test_save_running_config(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.save,
            self.ftp_path,
            'running',
        )

    def test_save_startup_config(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.save,
            self.ftp_path,
            'startup',
        )

    def test_orchestration_save_shallow(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.orchestration_save,
            'shallow',
        )

    def test_orchestration_save_deep(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.orchestration_save,
            'deep',
        )
