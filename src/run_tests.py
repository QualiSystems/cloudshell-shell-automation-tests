import unittest
from StringIO import StringIO

from src.configs import ResourceConfig, CloudShellConfig
from src.cs_handler import CloudShellHandler
from src.do_handler import DoHandler
from src.resource_handler import ResourceHandler
from src.smb_handler import SMB
from automation_tests.test_autoload import TestAutoload
from automation_tests.test_driver_installed import TestDriverInstalled
from automation_tests.test_run_custom_command import TestRunCustomCommand


CLOUDSHELL_SERVER_NAME = 'User-PC'
CLOUDSHELL_VERSION = '8.3'


def _run_tests(resource_handler, *test_cases):
    test_result = StringIO()
    test_loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for test_case in test_cases:
        for test_name in test_loader.getTestCaseNames(test_case):
            suite.addTest(test_case(test_name, resource_handler))

    unittest.TextTestRunner(test_result).run(suite)
    return test_result.getvalue()


def tests_without_device(conf, cs_handler, logger):
    with ResourceHandler(
            cs_handler,
            conf.shell_path,
            conf.dependencies_path,
            '127.0.0.1',
            conf.resource_name,
            logger) as fake_resource_handler:

        if conf.attributes:
            fake_resource_handler.set_attributes(conf.attributes)

        return _run_tests(fake_resource_handler, TestDriverInstalled)


def tests_with_device(conf, cs_handler, logger):
    with ResourceHandler(
            cs_handler,
            conf.shell_path,
            conf.dependencies_path,
            conf.device_ip,
            conf.resource_name,
            logger) as resource_handler:

        resource_handler.set_attributes(conf.attributes)

        return _run_tests(resource_handler, TestAutoload, TestRunCustomCommand)


def run_tests(conf, logger):
    if conf.cs.os_user and conf.cs.os_password:
        smb = SMB(
            conf.cs.os_user, conf.cs.os_password, conf.cs.host, CLOUDSHELL_SERVER_NAME, logger)
    else:
        smb = None

    cs_handler = CloudShellHandler(
        conf.cs.host, conf.cs.user, conf.cs.password, logger, conf.cs.domain, smb)

    if conf.device_ip:  # todo decide what tests to run
        result = tests_with_device(conf, cs_handler, logger)
    else:
        result = tests_without_device(conf, cs_handler, logger)

    return result


def main(conf, logger):
    """
    :param ResourceConfig conf:
    :param logging.Logger logger:
    """

    if conf.do:
        cs_handler = CloudShellHandler(
            conf.do.host, conf.do.user, conf.do.password, logger, conf.do.domain)
        do_handler = DoHandler(cs_handler, logger)

        try:
            ip, user, password, os_user, os_password = do_handler.get_new_cloudshell(
                CLOUDSHELL_VERSION)
            conf.cs = CloudShellConfig(ip, user, password, os_user, os_password)
            result = run_tests(conf, logger)
        finally:
            do_handler.end_reservation()

    else:
        result = run_tests(conf, logger)

    return result
