from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase


class TestDriverInstalled(BaseTestCase):

    def test_driver_installed(self):
        self.assertRaisesRegexp(
            CloudShellAPIError,
            r'SessionManagerException',
            self.resource_handler.run_custom_command,
            '',
        )
