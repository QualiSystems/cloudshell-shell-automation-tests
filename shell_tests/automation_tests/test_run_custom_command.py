from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseResourceServiceTestCase


class TestRunCustomCommand(BaseResourceServiceTestCase):
    def test_run_custom_command(self):
        output = self.handler.run_custom_command("show version")
        self.assertTrue(output)

    def test_run_custom_config_command(self):
        output = self.handler.run_custom_config_command("show version")
        self.assertTrue(output)


class TestRunCustomCommandWithoutDevice(BaseResourceServiceTestCase):
    def test_run_custom_command(self):
        with self.assertRaisesRegex(CloudShellAPIError, r"SessionManagerException"):
            self.handler.run_custom_command("show version")

    def test_run_custom_config_command(self):
        with self.assertRaisesRegex(CloudShellAPIError, r"SessionManagerException"):
            self.handler.run_custom_config_command("show version")


class TestRunCustomCommandShellFromTemplate(BaseResourceServiceTestCase):
    def test_run_custom_config_command(self):
        self.handler.run_custom_config_command("show version")

    def test_run_custom_command(self):
        self.handler.run_custom_command("show version")
