import json
import os

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.ftp_handler import FTPHandler


class TestSaveConfig(BaseTestCase):

    def setUp(self):
        super(TestSaveConfig, self).setUp()
        self.ftp_handler = FTPHandler(
            self.conf.ftp.host.split('://', 1)[-1],
            self.conf.ftp.user,
            self.conf.ftp.password,
            self.logger,
        )

    @property
    def ftp_path(self):
        try:
            scheme, host = self.conf.ftp.host.split('://')
        except ValueError:
            scheme = 'ftp'
            host = self.conf.ftp.host

        return '{}://{}:{}@{}'.format(scheme, self.conf.ftp.user, self.conf.ftp.password, host)

    def test_save_running_config(self):
        file_name = self.resource_handler.save(self.ftp_path, 'running')
        self.assertTrue(
            self.ftp_handler.get_file(file_name),
        )
        self.ftp_handler.delete_file(file_name)

    def test_save_startup_config(self):
        file_name = self.resource_handler.save(self.ftp_path, 'startup')
        self.assertTrue(
            self.ftp_handler.get_file(file_name),
        )
        self.ftp_handler.delete_file(file_name)

    def test_orchestration_save_shallow(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.ftp_path,
            }
        }

        saved_artifact_info = self.resource_handler.orchestration_save(
            'shallow', json.dumps(custom_params))

        self.assertTrue(saved_artifact_info)
        file_name = json.loads(saved_artifact_info)['saved_artifacts_info'][
            'saved_artifact']['identifier']
        file_name = os.path.basename(file_name)

        self.assertTrue(self.ftp_handler.get_file(file_name))
        self.ftp_handler.delete_file(file_name)

    def test_orchestration_save_deep(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.ftp_path,
            }
        }

        saved_artifact_info = self.resource_handler.orchestration_save(
            'deep', json.dumps(custom_params))

        self.assertTrue(saved_artifact_info)
        file_name = json.loads(saved_artifact_info)['saved_artifacts_info'][
            'saved_artifact']['identifier']
        file_name = os.path.basename(file_name)

        self.assertTrue(self.ftp_handler.get_file(file_name))
        self.ftp_handler.delete_file(file_name)


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
