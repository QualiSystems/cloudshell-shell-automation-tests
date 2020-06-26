import re

from cloudshell.api.common_cloudshell_api import CloudShellAPIError

from shell_tests.automation_tests.base import BaseResourceServiceTestCase
from shell_tests.errors import BaseAutomationException


class BaseControllerTestCase(BaseResourceServiceTestCase):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = True

    def setUp(self):
        if (
            self.RUN_AUTOLOAD_FOR_RELATED_RESOURCE
            and not self.handler.related_resource_handler.is_autoload_finished
        ):
            self.handler.related_resource_handler.autoload()


class TestLoadConfig(BaseControllerTestCase):
    def test_load_config(self):
        try:
            params = self.handler.tests_conf.params["load_config"]
            config_path = params.pop("config_file_location")
        except KeyError:
            raise BaseAutomationException(
                "You have to specify params for load_config command"
            )

        # just check that command runs without errors
        self.handler.load_config(config_path, params)


class TestStartTraffic(BaseControllerTestCase):
    def test_start_traffic(self):
        params = self.handler.tests_conf.params.get("start_traffic", {})
        self.handler.start_traffic(params)


class TestStopTraffic(BaseControllerTestCase):
    def test_stop_traffic(self):
        params = self.handler.tests_conf.params.get("stop_traffic", {})
        self.handler.stop_traffic(params)


class TestGetStatistics(BaseControllerTestCase):
    def test_get_statistics(self):
        params = self.handler.tests_conf.params.get("get_statistics", {})
        output = self.handler.get_statistics(params)
        self.assertTrue(output)


class TestGetTestFile(BaseControllerTestCase):
    def test_get_test_file(self):
        test_name = self.handler.tests_conf.params["get_test_file"]["test_name"]
        test_path = self.handler.get_test_file(test_name)
        dir_path, test_file_name = re.search(r"^(.*)[\\/](.*?)$", test_path).groups()
        if not dir_path.lower().startswith("c:\\"):
            raise BaseAutomationException("Test file have to locate under C:\\")

        dir_path = re.sub(r"^[Cc]:\\", "", dir_path)
        cs = self.sandbox_handler._cs_handler
        files = cs.smb.ls(cs.CS_SHARE, dir_path)

        file_names = map(lambda f: f.filename, files)
        self.assertIn(test_file_name, file_names)


class TestLoadConfigWithoutDevice(TestLoadConfig):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_load_config(self):
        error_pattern = r"(SessionManagerException|\'ConnectionError\')"
        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestLoadConfigWithoutDevice, self).test_load_config()


class TestStartTrafficWithoutDevice(TestStartTraffic):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_start_traffic(self):
        error_pattern = r"(SessionManagerException|\'ConnectionError\')"
        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestStartTrafficWithoutDevice, self).test_start_traffic()


class TestStopTrafficWithoutDevice(TestStopTraffic):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_stop_traffic(self):
        error_pattern = r"(SessionManagerException|\'ConnectionError\')"
        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestStopTrafficWithoutDevice, self).test_stop_traffic()


class TestGetStatisticsWithoutDevice(TestGetStatistics):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_get_statistics(self):
        error_pattern = r"(SessionManagerException|\'ConnectionError\')"
        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestGetStatisticsWithoutDevice, self).test_get_statistics()


class TestGetTestFileWithoutDevice(TestGetTestFile):
    RUN_AUTOLOAD_FOR_RELATED_RESOURCE = False

    def test_get_test_file(self):
        error_pattern = r"(SessionManagerException|\'ConnectionError\')"
        with self.assertRaisesRegexp(CloudShellAPIError, error_pattern):
            super(TestGetTestFileWithoutDevice, self).test_get_test_file()
