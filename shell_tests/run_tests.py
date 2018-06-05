import unittest
from StringIO import StringIO

from shell_tests.configs import ResourceConfig, CloudShellConfig
from shell_tests.cs_handler import CloudShellHandler
from shell_tests.do_handler import DoHandler
from shell_tests.resource_handler import ResourceHandler
from shell_tests.smb_handler import SMB
from shell_tests.automation_tests.test_autoload import TestAutoload, TestAutoloadWithoutDevice
from shell_tests.automation_tests.test_run_custom_command import TestRunCustomCommand, \
    TestRunCustomCommandWithoutDevice


class TestsRunner(object):
    CLOUDSHELL_SERVER_NAME = 'User-PC'
    CLOUDSHELL_VERSION = '8.3'

    def __init__(self, conf, logger):
        """Decide for tests need to run and run it

        :param ResourceConfig conf:
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

    @property
    def test_cases(self):
        """Return TestsCases based on config

        If we don't have a device (device IP) then just try to execute and wait for expected error
        If we have Attributes to connect to device via CLI then execute all tests
        Otherwise it's a simulator and we test only Autoload
        """

        if not self.conf.device_ip:
            self.logger.warning('We doesn\'t have a device so test only installing env and getting'
                                'an expected error')
            return [TestAutoloadWithoutDevice, TestRunCustomCommandWithoutDevice]
        elif self.conf.attributes.get('User'):
            return [TestAutoload, TestRunCustomCommand]
        else:
            self.logger.warning('We have only simulator so testing only an Autoload')
            return [TestAutoload]

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

        for test_case in self.test_cases:
            for test_name in test_loader.getTestCaseNames(test_case):
                suite.addTest(test_case(test_name, resource_handler))

        is_success = unittest.TextTestRunner(test_result, verbosity=2).run(suite).wasSuccessful()

        return is_success, test_result.getvalue()

    def run_tests(self):
        cs_handler = CloudShellHandler(
            self.conf.cs.host,
            self.conf.cs.user,
            self.conf.cs.password,
            self.logger,
            self.conf.cs.domain,
            self.smb_handler,
        )

        with ResourceHandler(
                cs_handler,
                self.conf.shell_path,
                self.conf.dependencies_path,
                self.conf.device_ip or '127.0.0.1',  # if we don't have a device to tests
                self.conf.resource_name,
                self.logger) as resource_handler:

            if self.conf.attributes:
                resource_handler.set_attributes(self.conf.attributes)

            return self.run_test_cases(resource_handler)

    def run(self):
        try:
            self.create_cloudshell_on_do()
            is_success, result = self.run_tests()
        finally:
            self.delete_cloudshell_on_do()

        return is_success, result
