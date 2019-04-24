import threading
import unittest
from StringIO import StringIO

from teamcity import is_running_under_teamcity
from teamcity.unittestpy import TeamcityTestRunner

from shell_tests.automation_tests.test_autoload import TestAutoloadNetworkDevices, \
    TestAutoloadWithoutDevice, TestAutoloadTrafficGeneratorDevices, TestAutoloadWithoutPorts, \
    TestAutoloadVirtualTrafficGeneratorDevices
from shell_tests.automation_tests.test_connectivity import TestConnectivity
from shell_tests.automation_tests.test_restore_config import TestRestoreConfigWithoutDevice, \
    TestRestoreConfig
from shell_tests.automation_tests.test_run_custom_command import TestRunCustomCommandWithoutDevice, \
    TestRunCustomCommand
from shell_tests.automation_tests.test_save_config import TestSaveConfigWithoutDevice, \
    TestSaveConfig
from shell_tests.automation_tests.test_traffic_generator_controller import TestLoadConfig, \
    TestLoadConfigWithoutDevice, TestStartTraffic, TestStopTraffic, TestGetStatistics, \
    TestStartTrafficWithoutDevice, TestStopTrafficWithoutDevice, TestGetStatisticsWithoutDevice, \
    TestGetTestFile, TestGetTestFileWithoutDevice
from shell_tests.helpers import get_driver_commands
from shell_tests.report_result import ResourceReport, SandboxReport, ServiceReport, \
    DeploymentResourceReport
from shell_tests.resource_handler import DeviceType


TEST_CASES_FIREWALL = {
    DeviceType.SIMULATOR: {
        'autoload': TestAutoloadNetworkDevices,
    },
    DeviceType.WITHOUT_DEVICE: {
        'autoload': TestAutoloadWithoutDevice,
        'run_custom_command': TestRunCustomCommandWithoutDevice,
        'run_custom_config_command': TestRunCustomCommandWithoutDevice,
        'save': TestSaveConfigWithoutDevice,
        'orchestration_save': TestSaveConfigWithoutDevice,
        'restore': TestRestoreConfigWithoutDevice,
        'orchestration_restore': TestRestoreConfigWithoutDevice,
    },
    DeviceType.REAL_DEVICE: {
        'autoload': TestAutoloadNetworkDevices,
        'run_custom_command': TestRunCustomCommand,
        'run_custom_config_command': TestRunCustomCommand,
        'save': TestSaveConfig,
        'orchestration_save': TestSaveConfig,
        'restore': TestRestoreConfig,
        'orchestration_restore': TestRestoreConfig,
    },
}
TEST_CASES_ROUTER = TEST_CASES_FIREWALL
TEST_CASES_ROUTER[DeviceType.REAL_DEVICE]['applyconnectivitychanges'] = TestConnectivity
TEST_CASES_SWITCH = TEST_CASES_ROUTER
TEST_CASES_TRAFFIC_GENERATOR_CHASSIS = {
    DeviceType.REAL_DEVICE: {
        'autoload': TestAutoloadTrafficGeneratorDevices,
    },
    DeviceType.WITHOUT_DEVICE: {
        'autoload': TestAutoloadWithoutDevice,
    },
    DeviceType.SIMULATOR: {
        'autoload': TestAutoloadTrafficGeneratorDevices,
    }
}
TEST_CASES_VIRTUAL_TRAFFIC_GENERATOR_CHASSIS = {
    DeviceType.REAL_DEVICE: {
        'autoload': TestAutoloadVirtualTrafficGeneratorDevices,
    },
}
TEST_CASES_TRAFFIC_GENERATOR_CONTROLLER = {
    DeviceType.REAL_DEVICE: {
        'load_config': TestLoadConfig,
        'start_traffic': TestStartTraffic,
        'stop_traffic': TestStopTraffic,
        'get_statistics': TestGetStatistics,
        'get_test_file': TestGetTestFile,
    },
    DeviceType.WITHOUT_DEVICE: {
        'load_config': TestLoadConfigWithoutDevice,
        'start_traffic': TestStartTrafficWithoutDevice,
        'stop_traffic': TestStopTrafficWithoutDevice,
        'get_statistics': TestGetStatisticsWithoutDevice,
        'get_test_file': TestGetTestFileWithoutDevice,
    }
}
TEST_CASES_GENERIC_APP_FAMILY = {
    DeviceType.REAL_DEVICE: {
        'autoload': TestAutoloadWithoutPorts,
    },
    DeviceType.WITHOUT_DEVICE: {
        'autoload': TestAutoloadWithoutDevice,
    }
}

TEST_CASES_MAP = {
    'CS_Firewall': TEST_CASES_FIREWALL,
    'CS_Router': TEST_CASES_ROUTER,
    'CS_Switch': TEST_CASES_SWITCH,
    'CS_TrafficGeneratorChassis': TEST_CASES_TRAFFIC_GENERATOR_CHASSIS,
    'CS_VirtualTrafficGeneratorChassis': TEST_CASES_VIRTUAL_TRAFFIC_GENERATOR_CHASSIS,
    'CS_TrafficGeneratorController': TEST_CASES_TRAFFIC_GENERATOR_CONTROLLER,
    'CS_GenericAppFamily': TEST_CASES_GENERIC_APP_FAMILY,
}
AUTOLOAD_TEST_FOR_FAMILIES = {
    'CS_Router',
    'CS_Firewall',
    'CS_Switch',
    'CS_TrafficGeneratorChassis',
    'CS_VirtualTrafficGeneratorChassis',
    'CS_GenericAppFamily',
}


class PatchedTestSuite(unittest.TestSuite):
    def __init__(self, *args, **kwargs):
        super(PatchedTestSuite, self).__init__(*args, **kwargs)
        self.result = None
        self._stop = False

    def run(self, result):
        if self._stop:
            result.stop()

        self.result = result
        super(PatchedTestSuite, self).run(result)

    def stop(self):
        self._stop = True

        if self.result:
            self.result.stop()


class RunTestsForSandbox(threading.Thread):
    REPORT_LOCK = threading.Lock()

    def __init__(self, sandbox_handler, logger, reporting):
        """Run Tests based on the Sandbox.

        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        :type logger: logging.Logger
        :type reporting: shell_tests.report_result.Reporting
        """
        super(RunTestsForSandbox, self).__init__(
            name='Thread-{}'.format(sandbox_handler.name))

        self.sandbox_handler = sandbox_handler
        self.logger = logger
        self.reporting = reporting

        self._stop = False
        self.current_test_suite = None
        self._test_runner = None

    def stop(self):
        if self.current_test_suite:
            self.current_test_suite.stop()
        self._stop = True

    def run(self):
        """Run tests for the Sandbox and resources."""
        with self.sandbox_handler:
            if self._stop:
                raise KeyboardInterrupt

            sandbox_report = self.run_sandbox_tests()

            for deployment_resource_handler in self.sandbox_handler.deployment_resource_handlers:
                if deployment_resource_handler.tests_conf.run_tests:
                    report = self.run_deployment_resource_tests(deployment_resource_handler)
                    sandbox_report.deployment_resources_reports.append(report)

            for resource_handler in self.sandbox_handler.resource_handlers:
                if resource_handler.tests_conf.run_tests:
                    resource_report = self.run_resource_tests(resource_handler)
                    sandbox_report.resources_reports.append(resource_report)

            for service_handler in self.sandbox_handler.service_handlers:
                if service_handler.tests_conf.run_tests:
                    service_report = self.run_service_tests(service_handler)
                    sandbox_report.services_reports.append(service_report)

        with self.REPORT_LOCK:
            self.reporting.sandboxes_reports.append(sandbox_report)

    @property
    def test_runner(self):
        if self._test_runner is None:
            if is_running_under_teamcity():
                self.logger.debug('Using TeamCity Test Runner')
                self._test_runner = TeamcityTestRunner
            else:
                self.logger.debug('Using Text Test Runner')
                self._test_runner = unittest.TextTestRunner

        return self._test_runner

    def run_sandbox_tests(self):
        """Run tests based on the sandbox and config.

        :rtype: SandboxReport
        """
        return SandboxReport(self.sandbox_handler.name, True, '')

    def _run_target_tests(self, target_handler):
        """Run tests based on the target type and config.

        :type target_handler: shell_tests.resource_handler.ResourceHandler|shell_tests.resource_handler.ServiceHandler
        :rtype (bool, str)
        :return: is success and tests result
        """
        self.current_test_suite = PatchedTestSuite()

        if target_handler.device_type == DeviceType.WITHOUT_DEVICE:
            self.logger.warning(
                '"{}" is a fake device so test only installing env '
                'and trying to execute commands and getting an expected '
                'error for connection'.format(target_handler.name))
        elif target_handler.device_type == DeviceType.SIMULATOR:
            self.logger.warning(
                '"{}" is a simulator so testing only an Autoload'.format(target_handler.name))

        test_cases_map = TEST_CASES_MAP[target_handler.family][target_handler.device_type]

        if target_handler.family in AUTOLOAD_TEST_FOR_FAMILIES:
            test_cases = [test_cases_map.get('autoload')]
        else:
            test_cases = []

        for command in get_driver_commands(target_handler.shell_handler.shell_path):
            test_case = test_cases_map.get(command.lower())
            if test_case and test_case not in test_cases:
                test_cases.append(test_case)

        for test_case in test_cases:
            for test_name in unittest.TestLoader().getTestCaseNames(test_case):
                test_inst = test_case(
                    test_name,
                    self.logger,
                    target_handler,
                    self.sandbox_handler,
                )

                self.current_test_suite.addTest(test_inst)

        test_result = StringIO()
        is_success = self.test_runner(
            test_result, verbosity=2,
        ).run(self.current_test_suite).wasSuccessful()

        self.current_test_suite = None
        return is_success, test_result.getvalue()

    def run_resource_tests(self, resource_handler):
        """Run tests based on the resource type and config.

        :type resource_handler: shell_tests.resource_handler.ResourceHandler
        :rtype: ResourceReport
        """
        is_success, test_result = self._run_target_tests(resource_handler)

        return ResourceReport(
            resource_handler.name,
            resource_handler.device_ip,
            resource_handler.device_type,
            resource_handler.family,
            is_success,
            test_result,
        )

    def run_deployment_resource_tests(self, deployment_resource_handler):
        """Run tests based on the deployment resource type and config.

        :type deployment_resource_handler: shell_tests.resource_handler.DeploymentResourceHandler
        :rtype: DeploymentResourceReport
        """
        is_success, test_result = self._run_target_tests(deployment_resource_handler)

        return DeploymentResourceReport(
            deployment_resource_handler.name,
            deployment_resource_handler.device_ip,
            deployment_resource_handler.device_type,
            deployment_resource_handler.family,
            is_success,
            test_result,
        )

    def run_service_tests(self, service_handler):
        """Run tests based on the service type and config.

        :type service_handler: shell_tests.resource_handler.ServiceHandler
        :rtype: ServiceReport
        """
        is_success, test_result = self._run_target_tests(service_handler)

        return ServiceReport(
            service_handler.name,
            service_handler.device_type,
            service_handler.family,
            is_success,
            test_result,
        )
