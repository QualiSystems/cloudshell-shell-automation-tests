import io
import re
import threading
import unittest
import zipfile
from StringIO import StringIO
from xml.etree import ElementTree

from teamcity import is_running_under_teamcity
from teamcity.unittestpy import TeamcityTestRunner

from shell_tests.automation_tests.test_autoload import TestAutoload, TestAutoloadWithoutDevice
from shell_tests.automation_tests.test_connectivity import TestConnectivity
from shell_tests.automation_tests.test_restore_config import TestRestoreConfigWithoutDevice, \
    TestRestoreConfig
from shell_tests.automation_tests.test_run_custom_command import TestRunCustomCommandWithoutDevice, \
    TestRunCustomCommand
from shell_tests.automation_tests.test_save_config import TestSaveConfigWithoutDevice, \
    TestSaveConfig
from shell_tests.resource_handler import ResourceHandler


TEST_CASES_MAP = {
    ResourceHandler.SIMULATOR: {
        'autoload': TestAutoload,
    },
    ResourceHandler.WITHOUT_DEVICE: {
        'autoload': TestAutoloadWithoutDevice,
        'run_custom_command': TestRunCustomCommandWithoutDevice,
        'run_custom_config_command': TestRunCustomCommandWithoutDevice,
        'save': TestSaveConfigWithoutDevice,
        'orchestration_save': TestSaveConfigWithoutDevice,
        'restore': TestRestoreConfigWithoutDevice,
        'orchestration_restore': TestRestoreConfigWithoutDevice,
    },
    ResourceHandler.REAL_DEVICE: {
        'autoload': TestAutoload,
        'run_custom_command': TestRunCustomCommand,
        'run_custom_config_command': TestRunCustomCommand,
        'save': TestSaveConfig,
        'orchestration_save': TestSaveConfig,
        'restore': TestRestoreConfig,
        'orchestration_restore': TestRestoreConfig,
        'applyconnectivitychanges': TestConnectivity,
    },
}


class RunTestsForResource(threading.Thread):
    REPORT_LOCK = threading.Lock()

    def __init__(self, cs_handler, shell_conf, resource_conf, shell_handler, logger, report):
        """Run Tests for the Resource.

        :param shell_tests.cs_handler.CloudShellHandler cs_handler:
        :param shell_tests.configs.ShellConfig shell_conf:
        :param shell_tests.configs.ResourceConfig resource_conf:
        :param shell_tests.shell_handler.ShellHandler shell_handler:
        :param logging.Logger logger:
        :param shell_tests.report_result.Reporting report:
        """
        super(RunTestsForResource, self).__init__()

        self.cs_handler = cs_handler
        self.shell_conf = shell_conf
        self.resource_conf = resource_conf
        self.shell_handler = shell_handler
        self.logger = logger
        self.report = report

        self.resource_handler = ResourceHandler(
            cs_handler,
            resource_conf.device_ip,
            resource_conf.resource_name,
            shell_conf.shell_path,
            logger,
        )

    def run(self):
        is_success, result = self.run_test_cases()

        with self.REPORT_LOCK:
            self.report.add_resource_report(
                self.resource_conf.resource_name,
                self.resource_conf.device_ip,
                self.resource_handler.device_type,
                is_success,
                result,
            )

    def run_test_cases(self):
        test_result = StringIO()
        test_loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        with self.resource_handler:
            if self.resource_conf.attributes:
                self.resource_handler.set_attributes(self.resource_conf.attributes)

            for test_case in self.resource_test_cases:
                for test_name in test_loader.getTestCaseNames(test_case):
                    suite.addTest(
                        test_case(
                            test_name,
                            self.resource_handler,
                            self.shell_conf,
                            self.resource_conf,
                            self.logger)
                    )

            if is_running_under_teamcity():
                self.logger.debug('Using TeamCity Test Runner')
                runner = TeamcityTestRunner
            else:
                self.logger.debug('Using Text Test Runner')
                runner = unittest.TextTestRunner

            is_success = runner(test_result, verbosity=2).run(suite).wasSuccessful()

            return is_success, test_result.getvalue()

    @property
    def resource_test_cases(self):
        """Return TestsCases based on resource

        If we don't have a device (device IP) then just try to execute and wait for expected error
        If we have Attributes to connect to device via CLI then execute all tests
        Otherwise it's a simulator and we test only Autoload
        """
        if self.resource_handler.device_type == self.resource_handler.WITHOUT_DEVICE:
            self.logger.warning(
                'We doesn\'t have a device so test only installing env and trying to execute '
                'commands and getting an expected error for connection')
        elif self.resource_handler.device_type == self.resource_handler.SIMULATOR:
            self.logger.warning('We have only simulator so testing only an Autoload')

        with zipfile.ZipFile(self.resource_handler.shell_path) as zip_file:

            driver_name = re.search(r'\'(\S+\.zip)', str(zip_file.namelist())).group(1)
            driver_file = io.BytesIO(zip_file.read(driver_name))

            with zipfile.ZipFile(driver_file) as driver_zip:
                driver_metadata = driver_zip.read('drivermetadata.xml')

        test_cases = [TEST_CASES_MAP[self.resource_handler.device_type]['autoload']]

        for command in self.get_driver_commands(driver_metadata):
            test_case = TEST_CASES_MAP[self.resource_handler.device_type].get(command.lower())
            if test_case and test_case not in test_cases:
                test_cases.append(test_case)

        return test_cases

    @staticmethod
    def get_driver_commands(driver_metadata):
        doc = ElementTree.fromstring(driver_metadata)
        commands = doc.findall('Layout/Category/Command')
        commands.extend(doc.findall('Layout/Command'))
        return [command.get('Name') for command in commands]
