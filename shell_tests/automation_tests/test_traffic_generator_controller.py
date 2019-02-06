from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.errors import BaseAutomationException


class TestLoadConfig(BaseTestCase):
    def test_load_config(self):
        try:
            params = self.target_handler.tests_conf.params['load_config']
            config_path = params['config_file_location']
            use_ports = params.get('use_ports_from_reservation')
        except KeyError:
            raise BaseAutomationException('You have to specify params for load_config command')

        kwargs = {'config_path': config_path}
        if use_ports:
            kwargs['use_ports_from_res'] = use_ports

        # just check that command runs without errors
        self.target_handler.load_config(**kwargs)


class TestLoadConfigWithoutDevice(TestLoadConfig):
    def test_load_config(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestLoadConfigWithoutDevice, self).test_load_config()
