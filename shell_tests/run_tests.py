import io
import re
import unittest
import zipfile
from StringIO import StringIO
from xml.etree import ElementTree

from shell_tests.automation_tests.test_connectivity import TestConnectivity
from shell_tests.automation_tests.test_restore_config import TestRestoreConfig, \
    TestRestoreConfigWithoutDevice
from shell_tests.automation_tests.test_save_config import TestSaveConfig, \
    TestSaveConfigWithoutDevice
from shell_tests.configs import ShellConfig, CloudShellConfig
from shell_tests.cs_handler import CloudShellHandler
from shell_tests.do_handler import DoHandler
from shell_tests.report_result import Reporting
from shell_tests.resource_handler import ResourceHandler
from shell_tests.smb_handler import SMB
from shell_tests.automation_tests.test_autoload import TestAutoload, TestAutoloadWithoutDevice
from shell_tests.automation_tests.test_run_custom_command import TestRunCustomCommand, \
    TestRunCustomCommandWithoutDevice


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


class TestsRunner(object):
    CLOUDSHELL_SERVER_NAME = 'User-PC'
    CLOUDSHELL_VERSION = '8.3'

    def __init__(self, conf, logger):
        """Decide for tests need to run and run it

        :param ShellConfig conf:
        :param logging.Logger logger:
        """

        self.conf = conf
        self.logger = logger

        self._do_handler = None
        self._smb_handler = None

    @property
    def do_handler(self):
        if self._do_handler is None and self.conf.do:
            cs_handler = CloudShellHandler(
                self.conf.do.host,
                self.conf.do.user,
                self.conf.do.password,
                self.logger,
                self.conf.do.domain,
            )
            self._do_handler = DoHandler(cs_handler, self.logger)

        return self._do_handler

    @property
    def smb_handler(self):
        if self._smb_handler is None and self.conf.cs.os_user:
            self._smb_handler = SMB(
                self.conf.cs.os_user,
                self.conf.cs.os_password,
                self.conf.cs.host,
                self.CLOUDSHELL_SERVER_NAME,
                self.logger,
            )

        return self._smb_handler

    @staticmethod
    def get_driver_commands(driver_metadata):
        doc = ElementTree.fromstring(driver_metadata)

        commands = doc.findall('Layout/Category/Command')
        commands.extend(doc.findall('Layout/Command'))
        return [command.get('Name') for command in commands]

    def get_test_cases(self, resource_handler):
        """Return TestsCases based on resource

        If we don't have a device (device IP) then just try to execute and wait for expected error
        If we have Attributes to connect to device via CLI then execute all tests
        Otherwise it's a simulator and we test only Autoload
        """

        if resource_handler.device_type == resource_handler.WITHOUT_DEVICE:
            self.logger.warning(
                'We doesn\'t have a device so test only installing env and getting an expected '
                'error')
        elif resource_handler.device_type == resource_handler.SIMULATOR:
            self.logger.warning('We have only simulator so testing only an Autoload')

        with zipfile.ZipFile(resource_handler.shell_path) as zip_file:

            driver_name = re.search(r'\'(\S+\.zip)', str(zip_file.namelist())).group(1)
            driver_file = io.BytesIO(zip_file.read(driver_name))

            with zipfile.ZipFile(driver_file) as driver_zip:
                driver_metadata = driver_zip.read('drivermetadata.xml')

        test_cases = [TEST_CASES_MAP[resource_handler.device_type]['autoload']]

        for command in self.get_driver_commands(driver_metadata):
            test_case = TEST_CASES_MAP[resource_handler.device_type].get(command.lower())
            if test_case and test_case not in test_cases:
                test_cases.append(test_case)

        return test_cases

    def create_cloudshell_on_do(self):
        """Create CloudShell instance on Do"""

        if self.do_handler:
            cs_config = CloudShellConfig(
                *self.do_handler.get_new_cloudshell(self.CLOUDSHELL_VERSION)
            )
            self.conf.cs = cs_config

    def delete_cloudshell_on_do(self):
        """Ends CloudShell reservation on Do"""

        if self.do_handler:
            self.do_handler.end_reservation()

    def run_test_cases(self, resource_handler):
        """Run tests for resource handler"""

        test_result = StringIO()
        test_loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        for test_case in self.get_test_cases(resource_handler):
            for test_name in test_loader.getTestCaseNames(test_case):
                suite.addTest(test_case(test_name, resource_handler, self.conf, self.logger))

        is_success = unittest.TextTestRunner(test_result, verbosity=2).run(suite).wasSuccessful()

        return is_success, test_result.getvalue()

    def run_tests(self):
        """Run tests in CloudShell for Shell on one or several devices

        :rtype: Reporting
        """

        cs_handler = CloudShellHandler(
            self.conf.cs.host,
            self.conf.cs.user,
            self.conf.cs.password,
            self.logger,
            self.conf.cs.domain,
            self.smb_handler,
        )

        report = Reporting(self.conf.shell_name)

        for resource_conf in self.conf.resources:
            with ResourceHandler(
                    cs_handler,
                    self.conf.shell_path,
                    self.conf.dependencies_path,
                    resource_conf.device_ip,
                    resource_conf.resource_name,
                    self.logger) as resource_handler:

                if resource_conf.attributes:
                    resource_handler.set_attributes(resource_conf.attributes)

                is_success, result = self.run_test_cases(resource_handler)

                report.add_resource_report(
                    resource_conf.resource_name,
                    resource_conf.device_ip,
                    resource_handler.device_type,
                    is_success,
                    result,
                )

        return report

    def run(self):
        try:
            self.create_cloudshell_on_do()
            report = self.run_tests()
        finally:
            self.delete_cloudshell_on_do()

        return report
