import json
import os

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.ftp_handler import FTPHandler


class TestRestoreConfig(BaseTestCase):

    def setUp(self):
        super(TestRestoreConfig, self).setUp()
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

    def test_restore_running_config_append(self):
        file_name = self.resource_handler.save(self.ftp_path, 'running')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.resource_handler.restore(config_file_path, 'running', 'append')
        finally:
            self.ftp_handler.delete_file(file_name)

    def test_restore_startup_config_append(self):
        file_name = self.resource_handler.save(self.ftp_path, 'startup')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.resource_handler.restore(config_file_path, 'startup', 'append')
        finally:
            self.ftp_handler.delete_file(file_name)

    def test_restore_running_config_override(self):
        file_name = self.resource_handler.save(self.ftp_path, 'running')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.resource_handler.restore(config_file_path, 'running', 'override')
        finally:
            self.ftp_handler.delete_file(file_name)

    def test_restore_startup_config_override(self):
        file_name = self.resource_handler.save(self.ftp_path, 'startup')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.resource_handler.restore(config_file_path, 'startup', 'override')
        finally:
            self.ftp_handler.delete_file(file_name)

    def test_orchestration_restore(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.ftp_path,
            }
        }

        saved_artifact_info = self.resource_handler.orchestration_save(
            'shallow', json.dumps(custom_params))
        try:
            self.resource_handler.orchestration_restore(
                saved_artifact_info,
                '',
            )
        finally:
            file_name = json.loads(saved_artifact_info)['saved_artifacts_info'][
                'saved_artifact']['identifier']
            file_name = os.path.basename(file_name)
            self.ftp_handler.delete_file(file_name)


class TestRestoreConfigWithoutDevice(TestRestoreConfig):
    FTP_PATH = 'ftp://localhost/test_conf'

    def test_restore_running_config_append(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.restore,
            self.FTP_PATH,
            'running',
            'append',
        )

    def test_restore_startup_config_append(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.restore,
            self.FTP_PATH,
            'startup',
            'append',
        )

    def test_restore_running_config_override(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.restore,
            self.FTP_PATH,
            'running',
            'override',
        )

    def test_restore_startup_config_override(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.restore,
            self.FTP_PATH,
            'startup',
            'override',
        )

    def test_orchestration_restore(self):
        saved_artifact_info = {
                'saved_artifacts_info': {
                    'saved_artifact': {
                        'artifact_type': 'local',
                        'identifier': '/device-running-130618-155327'},
                    'resource_name': self.resource_handler.resource_name,
                    'restore_rules': {'requires_same_resource': True},
                    'created_date': '2018-06-13T15:53:34.075000'}
            }

        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.orchestration_restore,
            json.dumps(saved_artifact_info),
        )
