import unittest

from shell_tests.configs import merge_dicts


class BaseTestCase(unittest.TestCase):
    def __init__(self, method_name, resource_handler, shell_conf, resource_conf, logger):
        """Base Test Case

        :param str method_name:
        :param shell_tests.resource_handler.ResourceHandler resource_handler:
        :param shell_tests.configs.ShellConfig shell_conf:
        :param shell_tests.configs.ResourceConfig resource_conf:
        :param logging.Logger logger:
        """

        super(BaseTestCase, self).__init__(method_name)
        self.resource_handler = resource_handler
        self.shell_conf = shell_conf
        self.resource_conf = resource_conf
        self.logger = logger

        test_name = '{}.{}'.format(self.__class__.__name__, method_name)

        expected_failures = merge_dicts(
            getattr(resource_conf.tests_conf, 'expected_failures', {}),
            getattr(shell_conf.tests_conf, 'expected_failures', {}),
        )

        reason = expected_failures.get(test_name)
        if reason:
            func = getattr(self, method_name)
            wrapped_func = self.expect_failure(func, reason)
            setattr(self, method_name, wrapped_func)

    def expect_failure(self, func, expected_message):
        def wrapped(*args, **kwargs):
            self.assertRaisesRegexp(
                Exception,
                expected_message,
                func,
                *args,
                **kwargs
            )
        return wrapped

    def id(self):
        id_ = super(BaseTestCase, self).id()
        return '{}-{}'.format(id_, self.resource_conf.name)
