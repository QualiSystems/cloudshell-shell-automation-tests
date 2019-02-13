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


class TestStartTraffic(BaseTestCase):
    def test_start_traffic(self):
        self.target_handler.start_traffic()


class TestStopTraffic(BaseTestCase):
    def test_stop_traffic(self):
        self.target_handler.stop_traffic()


class TestGetStatistics(BaseTestCase):
    def test_get_statistics(self):
        self.target_handler.get_statistics()


class TestLoadConfigWithoutDevice(TestLoadConfig):
    def test_load_config(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestLoadConfigWithoutDevice, self).test_load_config()


class TestStartTrafficWithoutDevice(TestStartTraffic):
    def test_start_traffic(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestStartTrafficWithoutDevice, self).test_start_traffic()


class TestStopTrafficWithoutDevice(TestStopTraffic):
    def test_stop_traffic(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestStopTrafficWithoutDevice, self).test_stop_traffic()


class TestGetStatisticsWithoutDevice(TestGetStatistics):
    def test_get_statistics(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestGetStatisticsWithoutDevice, self).test_get_statistics()
