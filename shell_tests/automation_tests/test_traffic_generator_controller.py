from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseTestCase
from shell_tests.errors import BaseAutomationException


class BaseControllerTestCase(BaseTestCase):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = True

    def setUp(self):
        if self.RUN_AUTOLOAD_FOR_RELATED_RESOURCE and \
                not self.target_handler.related_resource_handler.is_autoload_finished:
            self.target_handler.related_resource_handler.autoload()


class TestLoadConfig(BaseControllerTestCase):
    def test_load_config(self):
        try:
            params = self.target_handler.tests_conf.params['load_config']
            config_path = params.pop('config_file_location')
        except KeyError:
            raise BaseAutomationException('You have to specify params for load_config command')

        # just check that command runs without errors
        self.target_handler.load_config(config_path, params)


class TestStartTraffic(BaseControllerTestCase):
    def test_start_traffic(self):
        params = self.target_handler.tests_conf.params.get('start_traffic', {})
        self.target_handler.start_traffic(params)


class TestStopTraffic(BaseControllerTestCase):
    def test_stop_traffic(self):
        params = self.target_handler.tests_conf.params.get('stop_traffic', {})
        self.target_handler.stop_traffic(params)


class TestGetStatistics(BaseControllerTestCase):
    def test_get_statistics(self):
        params = self.target_handler.tests_conf.params.get('get_statistics', {})
        self.target_handler.get_statistics(params)


class TestLoadConfigWithoutDevice(TestLoadConfig):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_load_config(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestLoadConfigWithoutDevice, self).test_load_config()


class TestStartTrafficWithoutDevice(TestStartTraffic):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_start_traffic(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestStartTrafficWithoutDevice, self).test_start_traffic()


class TestStopTrafficWithoutDevice(TestStopTraffic):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_stop_traffic(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestStopTrafficWithoutDevice, self).test_stop_traffic()


class TestGetStatisticsWithoutDevice(TestGetStatistics):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_get_statistics(self):
        error_pattern = r'(SessionManagerException|\'ConnectionError\')'

        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestGetStatisticsWithoutDevice, self).test_get_statistics()
