import unittest


class BaseTestCase(unittest.TestCase):
    def __init__(self, method_name, logger):
        """Base Test Case.

        :type method_name: str
        :type logger: logging.Logger
        """
        super(BaseTestCase, self).__init__(method_name)
        self.logger = logger

    def add_decorator_for_expect_failed_func(self, method_name, tests_conf):
        test_name = '{}.{}'.format(type(self).__name__, method_name)

        reason = tests_conf.expected_failures.get(test_name)
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
        raise NotImplementedError('You have to create unique id for the test')


class BaseResourceServiceTestCase(BaseTestCase):
    def __init__(self, method_name, logger, target_handler, sandbox_handler):
        """Base Resource and Service Test Case.

        :type method_name: str
        :type logger: logging.Logger
        :type target_handler: shell_tests.resource_handler.ResourceHandler|shell_tests.resource_handler.ServiceHandler
        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        """
        super(BaseResourceServiceTestCase, self).__init__(method_name, logger)
        self.target_handler = target_handler
        self.sandbox_handler = sandbox_handler

        self.add_decorator_for_expect_failed_func(method_name, target_handler.tests_conf)

    def id(self):
        id_ = unittest.TestCase.id(self)
        return '{}-{}'.format(id_, self.target_handler.name)


class BaseSandboxTestCase(BaseTestCase):
    def __init__(self, method_name, logger, sandbox_handler):
        """Base Sandbox Test Case.

        :type method_name: str
        :type logger: logging.Logger
        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        """
        super(BaseSandboxTestCase, self).__init__(method_name, logger)
        self.sandbox_handler = sandbox_handler

        self.add_decorator_for_expect_failed_func(method_name, sandbox_handler.tests_conf)

    def id(self):
        id_ = unittest.TestCase.id(self)
        return '{}-{}'.format(id_, self.sandbox_handler.name)
