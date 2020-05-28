from io import StringIO
from typing import Tuple, Type
from unittest import TestLoader, TestSuite, TextTestRunner

from teamcity import is_running_under_teamcity
from teamcity.unittestpy import TeamcityTestRunner

from shell_tests.automation_tests.test_autoload import (
    TestAutoloadNetworkDevices,
    TestAutoloadTrafficGeneratorDevices,
    TestAutoloadVirtualTrafficGeneratorDevices,
    TestAutoloadWithoutDevice,
    TestAutoloadWithoutPorts,
)
from shell_tests.automation_tests.test_connectivity import TestConnectivity
from shell_tests.automation_tests.test_restore_config import (
    TestRestoreConfig,
    TestRestoreConfigWithoutDevice,
)
from shell_tests.automation_tests.test_run_custom_command import (
    TestRunCustomCommand,
    TestRunCustomCommandWithoutDevice,
)
from shell_tests.automation_tests.test_save_config import (
    TestSaveConfig,
    TestSaveConfigWithoutDevice,
)
from shell_tests.automation_tests.test_traffic_generator_controller import (
    TestGetStatistics,
    TestGetStatisticsWithoutDevice,
    TestGetTestFile,
    TestGetTestFileWithoutDevice,
    TestLoadConfig,
    TestLoadConfigWithoutDevice,
    TestStartTraffic,
    TestStartTrafficWithoutDevice,
    TestStopTraffic,
    TestStopTrafficWithoutDevice,
)
from shell_tests.handlers.resource_handler import DeviceType, ResourceHandler
from shell_tests.helpers.handler_storage import HandlerStorage
from shell_tests.helpers.logger import logger

TEST_CASES_FIREWALL = {
    DeviceType.SIMULATOR: {"autoload": TestAutoloadNetworkDevices},
    DeviceType.WITHOUT_DEVICE: {
        "autoload": TestAutoloadWithoutDevice,
        "run_custom_command": TestRunCustomCommandWithoutDevice,
        "run_custom_config_command": TestRunCustomCommandWithoutDevice,
        "save": TestSaveConfigWithoutDevice,
        "orchestration_save": TestSaveConfigWithoutDevice,
        "restore": TestRestoreConfigWithoutDevice,
        "orchestration_restore": TestRestoreConfigWithoutDevice,
    },
    DeviceType.REAL_DEVICE: {
        "autoload": TestAutoloadNetworkDevices,
        "run_custom_command": TestRunCustomCommand,
        "run_custom_config_command": TestRunCustomCommand,
        "save": TestSaveConfig,
        "orchestration_save": TestSaveConfig,
        "restore": TestRestoreConfig,
        "orchestration_restore": TestRestoreConfig,
    },
}
TEST_CASES_ROUTER = TEST_CASES_FIREWALL
TEST_CASES_ROUTER[DeviceType.REAL_DEVICE]["applyconnectivitychanges"] = TestConnectivity
TEST_CASES_SWITCH = TEST_CASES_ROUTER
TEST_CASES_TRAFFIC_GENERATOR_CHASSIS = {
    DeviceType.REAL_DEVICE: {"autoload": TestAutoloadTrafficGeneratorDevices},
    DeviceType.WITHOUT_DEVICE: {"autoload": TestAutoloadWithoutDevice},
    DeviceType.SIMULATOR: {"autoload": TestAutoloadTrafficGeneratorDevices},
}
TEST_CASES_VIRTUAL_TRAFFIC_GENERATOR_CHASSIS = {
    DeviceType.REAL_DEVICE: {"autoload": TestAutoloadVirtualTrafficGeneratorDevices},
}
TEST_CASES_TRAFFIC_GENERATOR_CONTROLLER = {
    DeviceType.REAL_DEVICE: {
        "load_config": TestLoadConfig,
        "start_traffic": TestStartTraffic,
        "stop_traffic": TestStopTraffic,
        "get_statistics": TestGetStatistics,
        "get_test_file": TestGetTestFile,
    },
    DeviceType.WITHOUT_DEVICE: {
        "load_config": TestLoadConfigWithoutDevice,
        "start_traffic": TestStartTrafficWithoutDevice,
        "stop_traffic": TestStopTrafficWithoutDevice,
        "get_statistics": TestGetStatisticsWithoutDevice,
        "get_test_file": TestGetTestFileWithoutDevice,
    },
}
TEST_CASES_GENERIC_APP_FAMILY = {
    DeviceType.REAL_DEVICE: {"autoload": TestAutoloadWithoutPorts},
    DeviceType.WITHOUT_DEVICE: {"autoload": TestAutoloadWithoutDevice},
}

TEST_CASES_MAP = {
    "CS_Firewall": TEST_CASES_FIREWALL,
    "CS_Router": TEST_CASES_ROUTER,
    "CS_Switch": TEST_CASES_SWITCH,
    "CS_TrafficGeneratorChassis": TEST_CASES_TRAFFIC_GENERATOR_CHASSIS,
    "CS_VirtualTrafficGeneratorChassis": TEST_CASES_VIRTUAL_TRAFFIC_GENERATOR_CHASSIS,
    "CS_TrafficGeneratorController": TEST_CASES_TRAFFIC_GENERATOR_CONTROLLER,
    "CS_GenericAppFamily": TEST_CASES_GENERIC_APP_FAMILY,
}
AUTOLOAD_TEST_FOR_FAMILIES = {
    "CS_Router",
    "CS_Firewall",
    "CS_Switch",
    "CS_TrafficGeneratorChassis",
    "CS_VirtualTrafficGeneratorChassis",
    "CS_GenericAppFamily",
}


class PatchedTestSuite(TestSuite):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.result = None
        self._stop = False

    def run(self, result):
        if self._stop:
            result.stop()

        self.result = result
        super().run(result)

    def stop(self):
        self._stop = True

        if self.result:
            self.result.stop()


def get_test_suite(
    handler: ResourceHandler, handler_storage: HandlerStorage
) -> PatchedTestSuite:
    if handler.device_type == DeviceType.WITHOUT_DEVICE:
        logger.warning(
            f'"{handler.name}" is a fake device so test only installing env and trying '
            f"to execute commands and getting an expected error for connection"
        )
    elif handler.device_type == DeviceType.SIMULATOR:
        logger.warning(f'"{handler.name}" is a simulator, testing only an Autoload')

    test_suite = PatchedTestSuite()
    test_cases_map = TEST_CASES_MAP[handler.family][handler.device_type]

    if handler.family in AUTOLOAD_TEST_FOR_FAMILIES:
        test_cases = [test_cases_map.get("autoload")]
    else:
        test_cases = []

    for command in handler.get_commands():
        test_case = test_cases_map.get(command.lower())
        if test_case and test_case not in test_cases:
            test_cases.append(test_case)

    for test_case in test_cases:
        for test_name in TestLoader().getTestCaseNames(test_case):
            test_inst = test_case(test_name, handler, handler_storage)
            test_suite.addTest(test_inst)

    return test_suite


def get_test_runner() -> Type[TextTestRunner]:
    if is_running_under_teamcity():
        logger.debug("Using TeamCity Test Runner")
        test_runner = TeamcityTestRunner
    else:
        logger.debug("Using Text Test Runner")
        test_runner = TextTestRunner
    return test_runner


def run_test_suite(
    test_runner: Type[TextTestRunner], test_suite: PatchedTestSuite
) -> Tuple[bool, str]:
    test_result = StringIO()
    is_success = test_runner(test_result, verbosity=2).run(test_suite).wasSuccessful()
    return is_success, test_result.getvalue()