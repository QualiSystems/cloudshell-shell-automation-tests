from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.ftp_handler import FTPHandler


class TestSaveConfig(BaseTestCase):

    def setUp(self):
        self.ftp_handler = FTPHandler(
            self.conf.ftp.host.split('://', 1)[-1],
            self.conf.ftp.user,
            self.conf.ftp.password,
            self.logger,
        )

    @property
    def ftp_path(self):
        try:
            scheme, path = self.conf.ftp.host.split('://')
        except ValueError:
            scheme = 'ftp'
            path = self.conf.ftp.host

        return '{}://{}:{}@{}'.format(scheme, self.conf.ftp.user, self.conf.ftp.password, path)

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
        self.assertTrue(self.resource_handler.orchestration_save('shallow'))

    def test_orchestration_save_deep(self):
        self.assertTrue(self.resource_handler.orchestration_save('deep'))


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
