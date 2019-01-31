import unittest


class BaseTestCase(unittest.TestCase):
    def __init__(self, method_name, resource_handler, sandbox_handler, logger):
        """Base Test Case.

        :type method_name: str
        :type resource_handler: shell_tests.resource_handler.ResourceHandler
        :type sandbox_handler: shell_tests.sandbox_handler.SandboxHandler
        :type logger: logging.Logger
        """
        super(BaseTestCase, self).__init__(method_name)
        self.resource_handler = resource_handler
        self.sandbox_handler = sandbox_handler
        self.logger = logger

        test_name = '{}.{}'.format(type(self).__name__, method_name)

        reason = resource_handler.tests_config.expected_failures.get(test_name)
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
        return '{}-{}'.format(id_, self.resource_handler.name)
