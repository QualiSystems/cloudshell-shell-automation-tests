import json

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseResourceServiceTestCase
from shell_tests.helpers import get_file_name_from_url


class TestRestoreConfig(BaseResourceServiceTestCase):

    @property
    def ftp_path(self):
        return 'ftp://{0.user}:{0.password}@{0.host}'.format(self.sandbox_handler.ftp_handler)

    def test_restore_running_config_append(self):
        file_name = self.target_handler.save(self.ftp_path, 'running')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'running', 'append')
        finally:
            self.sandbox_handler.ftp_handler.delete_file(file_name)

    def test_restore_startup_config_append(self):
        file_name = self.target_handler.save(self.ftp_path, 'startup')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'startup', 'append')
        finally:
            self.sandbox_handler.ftp_handler.delete_file(file_name)

    def test_restore_running_config_override(self):
        file_name = self.target_handler.save(self.ftp_path, 'running')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'running', 'override')
        finally:
            self.sandbox_handler.ftp_handler.delete_file(file_name)

    def test_restore_startup_config_override(self):
        file_name = self.target_handler.save(self.ftp_path, 'startup')
        config_file_path = '{}/{}'.format(self.ftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'startup', 'override')
        finally:
            self.sandbox_handler.ftp_handler.delete_file(file_name)

    def test_orchestration_restore(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.ftp_path,
            }
        }

        saved_artifact_info = self.target_handler.orchestration_save(
            'shallow', json.dumps(custom_params))
        try:
            self.target_handler.orchestration_restore(
                saved_artifact_info,
                '',
            )
        finally:
            path = json.loads(saved_artifact_info)['saved_artifacts_info'][
                'saved_artifact']['identifier']
            file_name = get_file_name_from_url(path)
            self.sandbox_handler.ftp_handler.delete_file(file_name)


class TestRestoreConfigFromScp(BaseResourceServiceTestCase):

    @property
    def scp_path(self):
        return 'scp://{0.user}:{0.password}@{0.host}'.format(self.sandbox_handler.scp_handler)

    def test_restore_running_config_append(self):
        file_name = self.target_handler.save(self.scp_path, 'running')
        config_file_path = '{}/{}'.format(self.scp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'running', 'append')
        finally:
            self.sandbox_handler.scp_handler.delete_file(file_name)

    def test_restore_startup_config_append(self):
        file_name = self.target_handler.save(self.scp_path, 'startup')
        config_file_path = '{}/{}'.format(self.scp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'startup', 'append')
        finally:
            self.sandbox_handler.scp_handler.delete_file(file_name)

    def test_restore_running_config_override(self):
        file_name = self.target_handler.save(self.scp_path, 'running')
        config_file_path = '{}/{}'.format(self.scp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'running', 'override')
        finally:
            self.sandbox_handler.scp_handler.delete_file(file_name)

    def test_restore_startup_config_override(self):
        file_name = self.target_handler.save(self.scp_path, 'startup')
        config_file_path = '{}/{}'.format(self.scp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'startup', 'override')
        finally:
            self.sandbox_handler.scp_handler.delete_file(file_name)

    def test_orchestration_restore(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.scp_path,
            }
        }

        saved_artifact_info = self.target_handler.orchestration_save(
            'shallow', json.dumps(custom_params))
        try:
            self.target_handler.orchestration_restore(
                saved_artifact_info,
                '',
            )
        finally:
            path = json.loads(saved_artifact_info)['saved_artifacts_info'][
                'saved_artifact']['identifier']
            file_name = get_file_name_from_url(path)
            self.sandbox_handler.scp_handler.delete_file(file_name)


class TestRestoreConfigFromTftp(BaseResourceServiceTestCase):

    @property
    def tftp_path(self):
        return 'tftp://{0.host}'.format(self.sandbox_handler.tftp_handler)

    def test_restore_running_config_append(self):
        file_name = self.target_handler.save(self.tftp_path, 'running')
        config_file_path = '{}/{}'.format(self.tftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'running', 'append')
        finally:
            self.sandbox_handler.tftp_handler.delete_file(file_name)

    def test_restore_startup_config_append(self):
        file_name = self.target_handler.save(self.tftp_path, 'startup')
        config_file_path = '{}/{}'.format(self.tftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'startup', 'append')
        finally:
            self.sandbox_handler.tftp_handler.delete_file(file_name)

    def test_restore_running_config_override(self):
        file_name = self.target_handler.save(self.tftp_path, 'running')
        config_file_path = '{}/{}'.format(self.tftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'running', 'override')
        finally:
            self.sandbox_handler.tftp_handler.delete_file(file_name)

    def test_restore_startup_config_override(self):
        file_name = self.target_handler.save(self.tftp_path, 'startup')
        config_file_path = '{}/{}'.format(self.tftp_path, file_name)

        try:
            self.target_handler.restore(config_file_path, 'startup', 'override')
        finally:
            self.sandbox_handler.tftp_handler.delete_file(file_name)

    def test_orchestration_restore(self):
        custom_params = {
            'custom_params': {
                'folder_path': self.tftp_path,
            }
        }

        saved_artifact_info = self.target_handler.orchestration_save(
            'shallow', json.dumps(custom_params))
        try:
            self.target_handler.orchestration_restore(
                saved_artifact_info,
                '',
            )
        finally:
            path = json.loads(saved_artifact_info)['saved_artifacts_info'][
                'saved_artifact']['identifier']
            file_name = get_file_name_from_url(path)
            self.sandbox_handler.tftp_handler.delete_file(file_name)


class TestRestoreConfigWithoutDevice(TestRestoreConfig):
    FTP_PATH = 'ftp://localhost/test_conf'

    def test_restore_running_config_append(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.target_handler.restore,
            self.FTP_PATH,
            'running',
            'append',
        )

    def test_restore_startup_config_append(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.target_handler.restore,
            self.FTP_PATH,
            'startup',
            'append',
        )

    def test_restore_running_config_override(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.target_handler.restore,
            self.FTP_PATH,
            'running',
            'override',
        )

    def test_restore_startup_config_override(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.target_handler.restore,
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
                    'resource_name': self.target_handler.name,
                    'restore_rules': {'requires_same_resource': True},
                    'created_date': '2018-06-13T15:53:34.075000'}
            }

        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.target_handler.orchestration_restore,
            json.dumps(saved_artifact_info),
        )

class TestRestoreConfigFromTemplate(BaseResourceServiceTestCase):
    def test_restore_running_config_append(self):
        self.target_handler.restore('ftp://', 'running', 'override')

    def test_orchestration_restore(self):
        saved_artifact_info = {
                'saved_artifacts_info': {
                    'saved_artifact': {
                        'artifact_type': 'local',
                        'identifier': '/device-running-130618-155327'},
                    'resource_name': 'resource_name',
                    'restore_rules': {'requires_same_resource': True},
                    'created_date': '2018-06-13T15:53:34.075000'}
            }

        self.target_handler.orchestration_restore(json.dumps(saved_artifact_info))