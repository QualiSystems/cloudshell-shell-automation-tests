from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase


class TestRunCustomCommand(BaseTestCase):

    def test_run_custom_command(self):
        output = self.resource_handler.run_custom_command('show version')

        self.assertTrue(output)

    def test_run_custom_config_command(self):
        output = self.resource_handler.run_custom_config_command('show version')

        self.assertTrue(output)


class TestRunCustomCommandWithoutDevice(BaseTestCase):

    def test_run_custom_command(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.run_custom_command,
            'show version',
        )

    def test_run_custom_config_command(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.run_custom_config_command,
            'show version',
        )
