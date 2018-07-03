import unittest

from cloudshell.api.common_cloudshell_api import CloudShellAPIError


class BaseTestCase(unittest.TestCase):
    def __init__(self, method_name, resource_handler, conf, logger):
        """Base Test Case

        :param str method_name:
        :param shell_tests.resource_handler.ResourceHandler resource_handler:
        :param shell_tests.configs.ShellConfig conf:
        :param logging.Logger logger:
        """

        super(BaseTestCase, self).__init__(method_name)
        self.resource_handler = resource_handler
        self.conf = conf
        self.logger = logger

        test_name = '{}.{}'.format(self.__class__.__name__, method_name)
        if self.conf.tests_conf and test_name in self.conf.tests_conf.expected_failures:
            reason = self.conf.tests_conf.expected_failures[test_name]
            func = getattr(self, method_name)
            wrapped_func = self.expect_failure(func, reason)
            setattr(self, method_name, wrapped_func)

    def expect_failure(self, func, expected_message):
        def wrapped(*args, **kwargs):
            self.assertRaisesRegexp(
                CloudShellAPIError,
                expected_message,
                func,
                *args,
                **kwargs
            )
        return wrapped
